"""埋め込みベクトル生成APIエンドポイント。"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ....application.use_cases.generate_embeddings import (
    GenerateEmbeddingsInput,
    GenerateEmbeddingsUseCase,
)
from ....domain.entities import User
from ....domain.exceptions import InvalidTextError, ModelNotAvailableError
from ..dependencies.auth import get_current_user
from ..dependencies.embeddings import get_generate_embeddings_use_case

router = APIRouter(
    prefix="/api/v1",
    tags=["embeddings"],
)


class GenerateEmbeddingsRequest(BaseModel):
    """埋め込み生成リクエスト。"""

    regenerate: bool = Field(
        default=False,
        description="既存の埋め込みを再生成するかどうか",
    )


class GenerateEmbeddingsResponse(BaseModel):
    """埋め込み生成レスポンス。"""

    document_id: str = Field(..., description="文書ID")
    chunk_count: int = Field(..., description="総チャンク数")
    embeddings_generated: int = Field(..., description="生成された埋め込み数")
    embeddings_skipped: int = Field(..., description="スキップされた埋め込み数")
    embedding_model: str = Field(..., description="使用されたモデル名")
    embedding_dimensions: int = Field(..., description="埋め込みベクトルの次元数")
    status: str = Field(..., description="処理ステータス")


class BatchGenerateEmbeddingsRequest(BaseModel):
    """バッチ埋め込み生成リクエスト。"""

    document_ids: list[str] = Field(
        ...,
        description="埋め込みを生成する文書IDのリスト",
        min_length=1,
        max_length=100,
    )
    regenerate: bool = Field(
        default=False,
        description="既存の埋め込みを再生成するかどうか",
    )


class BatchGenerateEmbeddingsResponse(BaseModel):
    """バッチ埋め込み生成レスポンス。"""

    total_documents: int = Field(..., description="処理対象文書数")
    successful: int = Field(..., description="成功した文書数")
    failed: int = Field(..., description="失敗した文書数")
    results: list[GenerateEmbeddingsResponse] = Field(
        ..., description="各文書の処理結果"
    )


@router.post(
    "/documents/{document_id}/embeddings",
    response_model=GenerateEmbeddingsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="文書の埋め込みベクトルを生成",
    description="指定された文書のチャンクから埋め込みベクトルを生成します。",
)
async def generate_embeddings(
    document_id: str,
    request: GenerateEmbeddingsRequest,
    use_case: GenerateEmbeddingsUseCase = Depends(get_generate_embeddings_use_case),
    current_user: User = Depends(get_current_user),
) -> GenerateEmbeddingsResponse:
    """文書の埋め込みベクトルを生成する。

    Args:
        document_id: 文書ID
        request: 埋め込み生成リクエスト
        use_case: 埋め込み生成ユースケース
        current_user: 現在のユーザー

    Returns:
        埋め込み生成結果

    Raises:
        HTTPException: 文書が見つからない場合（404）、モデルが利用できない場合（503）
    """
    try:
        # ユースケースを実行
        input_dto = GenerateEmbeddingsInput(
            document_id=document_id,
            regenerate=request.regenerate,
        )
        output = await use_case.execute(input_dto)

        return GenerateEmbeddingsResponse(
            document_id=output.document_id,
            chunk_count=output.chunk_count,
            embeddings_generated=output.embeddings_generated,
            embeddings_skipped=output.embeddings_skipped,
            embedding_model=output.embedding_model,
            embedding_dimensions=output.embedding_dimensions,
            status=output.status,
        )

    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            ) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except InvalidTextError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except ModelNotAvailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Embedding model not available: {e.model_name}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate embeddings",
        ) from e


@router.post(
    "/embeddings/batch",
    response_model=BatchGenerateEmbeddingsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="複数文書の埋め込みベクトルをバッチ生成",
    description="複数の文書の埋め込みベクトルを一括で生成します。",
)
async def batch_generate_embeddings(
    request: BatchGenerateEmbeddingsRequest,
    use_case: GenerateEmbeddingsUseCase = Depends(get_generate_embeddings_use_case),
    current_user: User = Depends(get_current_user),
) -> BatchGenerateEmbeddingsResponse:
    """複数文書の埋め込みベクトルをバッチ生成する。

    Args:
        request: バッチ埋め込み生成リクエスト
        use_case: 埋め込み生成ユースケース
        current_user: 現在のユーザー（editor権限以上が必要）

    Returns:
        バッチ処理結果

    Raises:
        HTTPException: 処理エラーが発生した場合
    """
    results = []
    successful = 0
    failed = 0

    for document_id in request.document_ids:
        try:
            input_dto = GenerateEmbeddingsInput(
                document_id=document_id,
                regenerate=request.regenerate,
            )
            output = await use_case.execute(input_dto)

            results.append(
                GenerateEmbeddingsResponse(
                    document_id=output.document_id,
                    chunk_count=output.chunk_count,
                    embeddings_generated=output.embeddings_generated,
                    embeddings_skipped=output.embeddings_skipped,
                    embedding_model=output.embedding_model,
                    embedding_dimensions=output.embedding_dimensions,
                    status=output.status,
                )
            )

            if output.status != "failed":
                successful += 1
            else:
                failed += 1

        except Exception:
            # エラーが発生した文書はスキップして続行
            failed += 1
            results.append(
                GenerateEmbeddingsResponse(
                    document_id=document_id,
                    chunk_count=0,
                    embeddings_generated=0,
                    embeddings_skipped=0,
                    embedding_model="",
                    embedding_dimensions=0,
                    status="failed",
                )
            )

    return BatchGenerateEmbeddingsResponse(
        total_documents=len(request.document_ids),
        successful=successful,
        failed=failed,
        results=results,
    )
