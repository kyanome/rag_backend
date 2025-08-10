"""RAG APIエンドポイント。

検索拡張生成（RAG）のAPIエンドポイントを定義する。
"""

from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ....application.use_cases.rag import (
    ProcessRAGQueryInput,
    ProcessRAGQueryOutput,
    ProcessRAGQueryUseCase,
)
from ....domain.entities import User
from ...dependencies import get_process_rag_query_use_case
from ..dependencies.auth import get_optional_current_user

router = APIRouter(prefix="/rag", tags=["RAG"])


class RAGQueryRequest(BaseModel):
    """RAGクエリリクエスト。

    Attributes:
        query: クエリテキスト
        search_type: 検索タイプ（keyword/vector/hybrid）
        max_results: 検索結果の最大数
        temperature: LLMの生成温度
        include_citations: 引用を含めるかどうか
        stream: ストリーミング応答を使用するか
        metadata: その他のメタデータ
    """

    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="質問テキスト",
        examples=["RAGシステムとは何ですか？"],
    )
    search_type: str = Field(
        default="hybrid",
        description="検索タイプ",
        examples=["hybrid"],
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=20,
        description="検索結果の最大数",
        examples=[5],
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="LLMの生成温度",
        examples=[0.7],
    )
    include_citations: bool = Field(
        default=True,
        description="引用を含めるかどうか",
        examples=[True],
    )
    stream: bool = Field(
        default=False,
        description="ストリーミング応答",
        examples=[False],
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="メタデータ",
        examples=[{"source": "web"}],
    )


class CitationResponse(BaseModel):
    """引用情報のレスポンス。

    Attributes:
        document_id: 文書ID
        document_title: 文書タイトル
        chunk_id: チャンクID
        chunk_index: チャンクインデックス
        content_snippet: 内容の抜粋
        relevance_score: 関連性スコア
    """

    document_id: str = Field(..., description="文書ID")
    document_title: str = Field(..., description="文書タイトル")
    chunk_id: str | None = Field(None, description="チャンクID")
    chunk_index: int | None = Field(None, description="チャンクインデックス")
    content_snippet: str = Field(..., description="内容の抜粋")
    relevance_score: float = Field(..., description="関連性スコア")


class RAGQueryResponse(BaseModel):
    """RAGクエリレスポンス。

    Attributes:
        answer_id: 応答ID
        query_id: クエリID
        answer: 回答テキスト
        citations: 引用情報
        confidence_score: 信頼度スコア
        confidence_level: 信頼度レベル
        search_results_count: 検索結果数
        processing_time_ms: 処理時間（ミリ秒）
        model_name: 使用したモデル名
        token_usage: トークン使用量
    """

    answer_id: str = Field(..., description="応答ID")
    query_id: str = Field(..., description="クエリID")
    answer: str = Field(..., description="回答テキスト")
    citations: list[CitationResponse] = Field(
        default_factory=list, description="引用情報"
    )
    confidence_score: float = Field(..., description="信頼度スコア")
    confidence_level: str = Field(..., description="信頼度レベル")
    search_results_count: int = Field(..., description="検索結果数")
    processing_time_ms: float = Field(..., description="処理時間（ミリ秒）")
    model_name: str = Field(..., description="使用したモデル名")
    token_usage: dict[str, int] = Field(
        default_factory=dict, description="トークン使用量"
    )

    @classmethod
    def from_use_case_output(cls, output: ProcessRAGQueryOutput) -> "RAGQueryResponse":
        """ユースケース出力から変換する。

        Args:
            output: ユースケース出力

        Returns:
            レスポンスDTO
        """
        citations = [
            CitationResponse(
                document_id=c.document_id,
                document_title=c.document_title,
                chunk_id=c.chunk_id,
                chunk_index=c.chunk_index,
                content_snippet=c.content_snippet,
                relevance_score=c.relevance_score,
            )
            for c in output.citations
        ]

        return cls(
            answer_id=output.answer_id,
            query_id=output.query_id,
            answer=output.answer_text,
            citations=citations,
            confidence_score=output.confidence_score,
            confidence_level=output.confidence_level,
            search_results_count=output.search_results_count,
            processing_time_ms=output.processing_time_ms,
            model_name=output.model_name,
            token_usage=output.token_usage,
        )


@router.post(
    "/query",
    response_model=RAGQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="RAGクエリを処理",
    description="質問に対してRAGを使用して回答を生成します",
)
async def process_rag_query(
    request: RAGQueryRequest,
    current_user: User | None = Depends(get_optional_current_user),
    use_case: ProcessRAGQueryUseCase = Depends(get_process_rag_query_use_case),
) -> RAGQueryResponse:
    """RAGクエリを処理する。

    Args:
        request: RAGクエリリクエスト
        current_user: 現在のユーザー（オプション）
        use_case: RAGユースケース

    Returns:
        RAGクエリレスポンス

    Raises:
        HTTPException: 処理エラー
    """
    try:
        # ユースケース入力を作成
        input_dto = ProcessRAGQueryInput(
            query_text=request.query,
            user_id=str(current_user.id.value) if current_user else None,
            search_type=request.search_type,
            max_results=request.max_results,
            temperature=request.temperature,
            include_citations=request.include_citations,
            stream=False,
            metadata=request.metadata,
        )

        # ユースケースを実行
        output = await use_case.execute(input_dto)

        # レスポンスを返す
        return RAGQueryResponse.from_use_case_output(output)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process RAG query: {str(e)}",
        ) from e


@router.post(
    "/query/stream",
    status_code=status.HTTP_200_OK,
    summary="RAGクエリをストリーミング処理",
    description="質問に対してRAGを使用してストリーミング形式で回答を生成します",
    response_class=StreamingResponse,
)
async def stream_rag_query(
    request: RAGQueryRequest,
    current_user: User | None = Depends(get_optional_current_user),
    use_case: ProcessRAGQueryUseCase = Depends(get_process_rag_query_use_case),
) -> StreamingResponse:
    """RAGクエリをストリーミング処理する。

    Args:
        request: RAGクエリリクエスト
        current_user: 現在のユーザー（オプション）
        use_case: RAGユースケース

    Returns:
        ストリーミングレスポンス

    Raises:
        HTTPException: 処理エラー
    """
    try:
        # ユースケース入力を作成
        input_dto = ProcessRAGQueryInput(
            query_text=request.query,
            user_id=str(current_user.id.value) if current_user else None,
            search_type=request.search_type,
            max_results=request.max_results,
            temperature=request.temperature,
            include_citations=request.include_citations,
            stream=True,
            metadata=request.metadata,
        )

        # ストリーミングジェネレーターを作成
        async def generate() -> AsyncIterator[bytes]:
            try:
                async for chunk in use_case.stream(input_dto):
                    yield chunk.encode("utf-8")
            except Exception as e:
                yield f"\n\nError: {str(e)}".encode()

        return StreamingResponse(
            generate(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "X-Content-Type-Options": "nosniff",
            },
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stream RAG response: {str(e)}",
        ) from e
