"""文書関連のAPIエンドポイント。"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from ....application.use_cases.upload_document import (
    UploadDocumentInput,
    UploadDocumentUseCase,
)
from ...dependencies import get_upload_document_use_case

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentUploadResponse(BaseModel):
    """文書アップロードレスポンス。"""

    document_id: str = Field(..., description="文書ID")
    title: str = Field(..., description="文書タイトル")
    file_name: str = Field(..., description="ファイル名")
    file_size: int = Field(..., description="ファイルサイズ（バイト）")
    content_type: str = Field(..., description="コンテンツタイプ")
    created_at: str = Field(..., description="作成日時（ISO形式）")

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "技術仕様書.pdf",
                "file_name": "技術仕様書.pdf",
                "file_size": 1048576,
                "content_type": "application/pdf",
                "created_at": "2024-01-01T00:00:00",
            }
        }


class ErrorResponse(BaseModel):
    """エラーレスポンス。"""

    detail: str = Field(..., description="エラーメッセージ")


@router.post(
    "/",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        413: {"model": ErrorResponse, "description": "Request Entity Too Large"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
    summary="文書をアップロード",
    description="文書ファイルをアップロードし、システムに登録します。",
)
async def upload_document(
    file: Annotated[UploadFile, File(description="アップロードするファイル")],
    title: Annotated[str | None, Form(description="文書タイトル")] = None,
    category: Annotated[str | None, Form(description="文書カテゴリ")] = None,
    tags: Annotated[str | None, Form(description="タグ（カンマ区切り）")] = None,
    author: Annotated[str | None, Form(description="作成者")] = None,
    description: Annotated[str | None, Form(description="文書の説明")] = None,
    use_case: UploadDocumentUseCase = Depends(get_upload_document_use_case),
) -> DocumentUploadResponse:
    """文書をアップロードする。

    Args:
        file: アップロードするファイル
        title: 文書タイトル（省略時はファイル名を使用）
        category: 文書カテゴリ
        tags: タグ（カンマ区切り）
        author: 作成者
        description: 文書の説明
        use_case: 文書アップロードユースケース

    Returns:
        アップロード結果

    Raises:
        HTTPException: エラーが発生した場合
    """
    try:
        # ファイル内容を読み込む
        file_content = await file.read()
        file_size = len(file_content)

        # タグをリストに変換
        tag_list = []
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

        # 入力DTOを作成
        input_dto = UploadDocumentInput(
            file_name=file.filename or "unknown",
            file_content=file_content,
            file_size=file_size,
            content_type=file.content_type or "application/octet-stream",
            title=title,
            category=category,
            tags=tag_list,
            author=author,
            description=description,
        )

        # ユースケースを実行
        output_dto = await use_case.execute(input_dto)

        # レスポンスを作成
        return DocumentUploadResponse(
            document_id=output_dto.document_id,
            title=output_dto.title,
            file_name=output_dto.file_name,
            file_size=output_dto.file_size,
            content_type=output_dto.content_type,
            created_at=output_dto.created_at,
        )

    except ValueError as e:
        # バリデーションエラー
        if "exceeds maximum allowed size" in str(e):
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=str(e),
            ) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        # その他のエラー
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload document: {str(e)}",
        ) from e
