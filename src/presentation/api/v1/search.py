"""文書検索APIエンドポイント。

DDDの原則に従い、検索機能をRESTful APIとして提供する。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ....application.use_cases.search_documents import (
    SearchDocumentsInput,
    SearchDocumentsUseCase,
)
from ....domain.value_objects import PageInfo
from ...dependencies import get_search_documents_use_case
from ..dependencies.auth import OptionalAuth

router = APIRouter(prefix="/search", tags=["search"])


class SearchRequest(BaseModel):
    """検索リクエストのDTO。

    Attributes:
        query: 検索クエリ文字列
        search_type: 検索タイプ（keyword/vector/hybrid）
        limit: 返す結果の最大数
        offset: スキップする件数
        similarity_threshold: ベクトル検索の類似度閾値
        highlight: 検索結果をハイライトするかどうか
    """

    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="検索クエリ",
        examples=["RAGシステム"],
    )
    search_type: str = Field(
        default="hybrid",
        description="検索タイプ",
        examples=["hybrid"],
        pattern="^(keyword|vector|hybrid)$",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="結果の最大数",
        examples=[10],
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="スキップする件数",
        examples=[0],
    )
    similarity_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="類似度の閾値",
        examples=[0.7],
    )
    highlight: bool = Field(
        default=True,
        description="検索結果をハイライトするかどうか",
        examples=[True],
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "RAGシステムの実装",
                "search_type": "hybrid",
                "limit": 10,
                "offset": 0,
                "similarity_threshold": 0.7,
                "highlight": True,
            }
        }


class SearchResultItem(BaseModel):
    """検索結果アイテムのDTO。

    Attributes:
        document_id: 文書ID
        document_title: 文書タイトル
        content_preview: 内容のプレビュー
        score: 関連性スコア（0.0〜1.0）
        match_type: マッチタイプ（keyword/vector/both）
        confidence_level: 信頼度レベル（high/medium/low）
        chunk_id: チャンクID（ベクトル検索の場合）
        chunk_index: チャンクインデックス（ベクトル検索の場合）
        highlights: ハイライト部分
    """

    document_id: str = Field(..., description="文書ID")
    document_title: str = Field(..., description="文書タイトル")
    content_preview: str = Field(..., description="内容のプレビュー（最大200文字）")
    score: float = Field(..., ge=0.0, le=1.0, description="関連性スコア")
    match_type: str = Field(..., description="マッチタイプ")
    confidence_level: str = Field(..., description="信頼度レベル")
    chunk_id: str | None = Field(None, description="チャンクID")
    chunk_index: int | None = Field(None, description="チャンクインデックス")
    highlights: list[str] = Field(default_factory=list, description="ハイライト部分")

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "document_title": "RAGシステム設計書",
                "content_preview": "RAGシステムは、検索拡張生成技術を用いて...",
                "score": 0.95,
                "match_type": "both",
                "confidence_level": "high",
                "chunk_id": "chunk-001",
                "chunk_index": 0,
                "highlights": ["<mark>RAGシステム</mark>は、検索拡張生成技術"],
            }
        }


class SearchResponse(BaseModel):
    """検索レスポンスのDTO。

    Attributes:
        results: 検索結果のリスト
        total_count: 総結果数
        search_time_ms: 検索にかかった時間（ミリ秒）
        query_type: 実行された検索タイプ
        query: 元の検索クエリ
        page_info: ページネーション情報
        high_confidence_count: 高信頼度の結果数
    """

    results: list[SearchResultItem] = Field(..., description="検索結果")
    total_count: int = Field(..., ge=0, description="総結果数")
    search_time_ms: float = Field(..., ge=0, description="検索時間（ミリ秒）")
    query_type: str = Field(..., description="検索タイプ")
    query: str = Field(..., description="検索クエリ")
    page_info: PageInfo = Field(..., description="ページネーション情報")
    high_confidence_count: int = Field(..., ge=0, description="高信頼度結果数")

    class Config:
        json_schema_extra = {
            "example": {
                "results": [
                    {
                        "document_id": "550e8400-e29b-41d4-a716-446655440000",
                        "document_title": "RAGシステム設計書",
                        "content_preview": "RAGシステムは、検索拡張生成技術を用いて...",
                        "score": 0.95,
                        "match_type": "both",
                        "confidence_level": "high",
                        "chunk_id": "chunk-001",
                        "chunk_index": 0,
                        "highlights": ["<mark>RAGシステム</mark>は、検索拡張生成技術"],
                    }
                ],
                "total_count": 42,
                "search_time_ms": 150.5,
                "query_type": "hybrid",
                "query": "RAGシステムの実装",
                "page_info": {
                    "page": 1,
                    "page_size": 10,
                    "total_pages": 5,
                    "total_count": 42,
                },
                "high_confidence_count": 15,
            }
        }


class ErrorResponse(BaseModel):
    """エラーレスポンスのDTO。"""

    detail: str = Field(..., description="エラーメッセージ")


def _add_highlights(text: str, query: str, enable_highlight: bool) -> list[str]:
    """テキストに検索クエリのハイライトを追加する。

    Args:
        text: 元のテキスト
        query: 検索クエリ
        enable_highlight: ハイライトを有効にするかどうか

    Returns:
        ハイライトされた部分のリスト
    """
    if not enable_highlight:
        return []

    highlights = []
    query_lower = query.lower()
    text_lower = text.lower()

    # 簡易的なハイライト実装（実際はより高度なアルゴリズムを使用）
    if query_lower in text_lower:
        start_idx = text_lower.index(query_lower)
        end_idx = start_idx + len(query)
        # 前後の文脈を含めて抽出
        context_start = max(0, start_idx - 20)
        context_end = min(len(text), end_idx + 20)
        highlighted = text[context_start:start_idx]
        highlighted += f"<mark>{text[start_idx:end_idx]}</mark>"
        highlighted += text[end_idx:context_end]
        highlights.append(highlighted)

    return highlights


@router.post(
    "/",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="文書を検索する",
    description="キーワード検索、ベクトル検索、またはハイブリッド検索を実行します。",
    responses={
        200: {"description": "検索成功", "model": SearchResponse},
        400: {"description": "不正なリクエスト", "model": ErrorResponse},
        500: {"description": "サーバーエラー", "model": ErrorResponse},
    },
)
async def search_documents(
    request: SearchRequest,
    use_case: Annotated[SearchDocumentsUseCase, Depends(get_search_documents_use_case)],
    auth: OptionalAuth,
) -> SearchResponse:
    """文書を検索する。

    Args:
        request: 検索リクエスト
        use_case: 検索ユースケース
        auth: オプショナル認証情報

    Returns:
        SearchResponse: 検索結果

    Raises:
        HTTPException: エラーが発生した場合
    """
    try:
        # 入力DTOを作成
        input_dto = SearchDocumentsInput(
            query=request.query,
            search_type=request.search_type,
            limit=request.limit,
            offset=request.offset,
            similarity_threshold=request.similarity_threshold,
            # 認証ユーザーがいる場合、そのユーザーの文書のみを検索対象にすることも可能
            # ここでは実装していないが、将来的な拡張ポイント
        )

        # ユースケースを実行
        output = await use_case.execute(input_dto)

        # レスポンスDTOを作成
        results = []
        for item in output.results:
            # ハイライト処理
            highlights = item.highlights or []
            if request.highlight and not highlights:
                highlights = _add_highlights(
                    item.content_preview, request.query, request.highlight
                )

            results.append(
                SearchResultItem(
                    document_id=item.document_id,
                    document_title=item.document_title,
                    content_preview=item.content_preview,
                    score=item.score,
                    match_type=item.match_type,
                    confidence_level=item.confidence_level,
                    chunk_id=item.chunk_id,
                    chunk_index=item.chunk_index,
                    highlights=highlights,
                )
            )

        # ページネーション情報を作成
        total_pages = (output.total_count + request.limit - 1) // request.limit
        current_page = (request.offset // request.limit) + 1

        page_info = PageInfo(
            page=current_page,
            page_size=request.limit,
            total_pages=total_pages,
            total_count=output.total_count,
        )

        return SearchResponse(
            results=results,
            total_count=output.total_count,
            search_time_ms=output.search_time_ms,
            query_type=output.query_type,
            query=output.query_text,
            page_info=page_info,
            high_confidence_count=output.high_confidence_count,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"検索処理中にエラーが発生しました: {str(e)}",
        ) from e
