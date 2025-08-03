"""文書関連のAPIエンドポイント。"""

from datetime import datetime
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field

from ....application.use_cases.delete_document import (
    DeleteDocumentInput,
    DeleteDocumentUseCase,
)
from ....application.use_cases.get_document import (
    GetDocumentInput,
    GetDocumentUseCase,
)
from ....application.use_cases.get_document_list import (
    GetDocumentListInput,
    GetDocumentListUseCase,
)
from ....application.use_cases.update_document import (
    UpdateDocumentInput,
    UpdateDocumentUseCase,
)
from ....application.use_cases.upload_document import (
    UploadDocumentInput,
    UploadDocumentUseCase,
)
from ....domain.exceptions.document_exceptions import (
    DocumentNotFoundError,
    DocumentValidationError,
)
from ....domain.value_objects import PageInfo
from ...dependencies import (
    get_delete_document_use_case,
    get_get_document_list_use_case,
    get_get_document_use_case,
    get_update_document_use_case,
    get_upload_document_use_case,
)

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


class DocumentListItemResponse(BaseModel):
    """文書リストアイテムのレスポンス。"""

    document_id: str = Field(..., description="文書ID")
    title: str = Field(..., description="文書タイトル")
    file_name: str = Field(..., description="ファイル名")
    file_size: int = Field(..., description="ファイルサイズ（バイト）")
    content_type: str = Field(..., description="コンテンツタイプ")
    category: str | None = Field(None, description="カテゴリ")
    tags: list[str] = Field(default_factory=list, description="タグリスト")
    author: str | None = Field(None, description="作成者")
    created_at: str = Field(..., description="作成日時（ISO形式）")
    updated_at: str = Field(..., description="更新日時（ISO形式）")

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "技術仕様書.pdf",
                "file_name": "技術仕様書.pdf",
                "file_size": 1048576,
                "content_type": "application/pdf",
                "category": "技術文書",
                "tags": ["仕様書", "設計"],
                "author": "山田太郎",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
            }
        }


class DocumentListResponse(BaseModel):
    """文書一覧のレスポンス。"""

    documents: list[DocumentListItemResponse] = Field(..., description="文書リスト")
    page_info: PageInfo = Field(..., description="ページ情報")

    class Config:
        json_schema_extra = {
            "example": {
                "documents": [
                    {
                        "document_id": "550e8400-e29b-41d4-a716-446655440000",
                        "title": "技術仕様書.pdf",
                        "file_name": "技術仕様書.pdf",
                        "file_size": 1048576,
                        "content_type": "application/pdf",
                        "category": "技術文書",
                        "tags": ["仕様書", "設計"],
                        "author": "山田太郎",
                        "created_at": "2024-01-01T00:00:00",
                        "updated_at": "2024-01-01T00:00:00",
                    }
                ],
                "page_info": {
                    "page": 1,
                    "page_size": 20,
                    "total_count": 1,
                    "total_pages": 1,
                },
            }
        }


class DocumentDetailResponse(BaseModel):
    """文書詳細のレスポンス。"""

    document_id: str = Field(..., description="文書ID")
    title: str = Field(..., description="文書タイトル")
    file_name: str = Field(..., description="ファイル名")
    file_size: int = Field(..., description="ファイルサイズ（バイト）")
    content_type: str = Field(..., description="コンテンツタイプ")
    category: str | None = Field(None, description="カテゴリ")
    tags: list[str] = Field(default_factory=list, description="タグリスト")
    author: str | None = Field(None, description="作成者")
    description: str | None = Field(None, description="文書の説明")
    created_at: str = Field(..., description="作成日時（ISO形式）")
    updated_at: str = Field(..., description="更新日時（ISO形式）")
    version: int = Field(..., description="バージョン番号")

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "技術仕様書.pdf",
                "file_name": "技術仕様書.pdf",
                "file_size": 1048576,
                "content_type": "application/pdf",
                "category": "技術文書",
                "tags": ["仕様書", "設計"],
                "author": "山田太郎",
                "description": "システムの技術仕様をまとめた文書です。",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "version": 1,
            }
        }


class DocumentUpdateRequest(BaseModel):
    """文書更新のリクエスト。"""

    title: str | None = Field(None, description="文書タイトル")
    category: str | None = Field(None, description="カテゴリ")
    tags: list[str] | None = Field(None, description="タグリスト")
    author: str | None = Field(None, description="作成者")
    description: str | None = Field(None, description="文書の説明")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "技術仕様書 v2.0",
                "category": "技術文書",
                "tags": ["仕様書", "設計", "v2.0"],
                "author": "山田太郎",
                "description": "システムの技術仕様をまとめた文書（更新版）です。",
            }
        }


class DocumentUpdateResponse(BaseModel):
    """文書更新のレスポンス。"""

    document_id: str = Field(..., description="文書ID")
    title: str = Field(..., description="文書タイトル")
    file_name: str = Field(..., description="ファイル名")
    file_size: int = Field(..., description="ファイルサイズ（バイト）")
    content_type: str = Field(..., description="コンテンツタイプ")
    category: str | None = Field(None, description="カテゴリ")
    tags: list[str] = Field(default_factory=list, description="タグリスト")
    author: str | None = Field(None, description="作成者")
    description: str | None = Field(None, description="文書の説明")
    created_at: str = Field(..., description="作成日時（ISO形式）")
    updated_at: str = Field(..., description="更新日時（ISO形式）")
    version: int = Field(..., description="バージョン番号")

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "技術仕様書 v2.0",
                "file_name": "技術仕様書.pdf",
                "file_size": 1048576,
                "content_type": "application/pdf",
                "category": "技術文書",
                "tags": ["仕様書", "設計", "v2.0"],
                "author": "山田太郎",
                "description": "システムの技術仕様をまとめた文書（更新版）です。",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-02T00:00:00",
                "version": 2,
            }
        }


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


@router.get(
    "/",
    response_model=DocumentListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
    summary="文書一覧を取得",
    description="文書の一覧をページネーションとフィルタリング機能付きで取得します。",
)
async def get_document_list(
    page: Annotated[int, Query(ge=1, description="ページ番号（1から開始）")] = 1,
    page_size: Annotated[
        int, Query(ge=1, le=100, description="1ページあたりの件数（最大100）")
    ] = 20,
    title: Annotated[
        str | None, Query(description="タイトル検索キーワード（部分一致）")
    ] = None,
    created_from: Annotated[
        datetime | None, Query(description="作成日時の開始（ISO形式）")
    ] = None,
    created_to: Annotated[
        datetime | None, Query(description="作成日時の終了（ISO形式）")
    ] = None,
    category: Annotated[str | None, Query(description="カテゴリ")] = None,
    tags: Annotated[str | None, Query(description="タグ（カンマ区切り）")] = None,
    use_case: GetDocumentListUseCase = Depends(get_get_document_list_use_case),
) -> DocumentListResponse:
    """文書一覧を取得する。

    Args:
        page: ページ番号（1から開始）
        page_size: 1ページあたりの件数（最大100）
        title: タイトル検索キーワード（部分一致）
        created_from: 作成日時の開始
        created_to: 作成日時の終了
        category: カテゴリ
        tags: タグ（カンマ区切り）
        use_case: 文書一覧取得ユースケース

    Returns:
        文書一覧レスポンス

    Raises:
        HTTPException: エラーが発生した場合
    """
    try:
        # タグをリストに変換
        tag_list = None
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

        # 入力DTOを作成
        input_dto = GetDocumentListInput(
            page=page,
            page_size=page_size,
            title=title,
            created_from=created_from,
            created_to=created_to,
            category=category,
            tags=tag_list,
        )

        # ユースケースを実行
        output_dto = await use_case.execute(input_dto)

        # レスポンスを作成
        document_responses = [
            DocumentListItemResponse(
                document_id=doc.document_id,
                title=doc.title,
                file_name=doc.file_name,
                file_size=doc.file_size,
                content_type=doc.content_type,
                category=doc.category,
                tags=doc.tags,
                author=doc.author,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
            )
            for doc in output_dto.documents
        ]

        return DocumentListResponse(
            documents=document_responses, page_info=output_dto.page_info
        )

    except ValueError as e:
        # バリデーションエラー
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        # その他のエラー
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get document list: {str(e)}",
        ) from e


@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Not Found"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
    summary="文書詳細を取得",
    description="指定されたIDの文書の詳細情報を取得します。",
)
async def get_document(
    document_id: str,
    use_case: GetDocumentUseCase = Depends(get_get_document_use_case),
) -> DocumentDetailResponse:
    """文書詳細を取得する。

    Args:
        document_id: 文書ID
        use_case: 文書詳細取得ユースケース

    Returns:
        文書詳細レスポンス

    Raises:
        HTTPException: エラーが発生した場合
    """
    try:
        # 入力DTOを作成
        input_dto = GetDocumentInput(document_id=document_id)

        # ユースケースを実行
        output_dto = await use_case.execute(input_dto)

        # レスポンスを作成
        return DocumentDetailResponse(
            document_id=output_dto.document_id,
            title=output_dto.title,
            file_name=output_dto.file_name,
            file_size=output_dto.file_size,
            content_type=output_dto.content_type,
            category=output_dto.category,
            tags=output_dto.tags,
            author=output_dto.author,
            description=output_dto.description,
            created_at=output_dto.created_at,
            updated_at=output_dto.updated_at,
            version=output_dto.version,
        )

    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id '{document_id}' not found",
        ) from None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get document: {str(e)}",
        ) from e


@router.put(
    "/{document_id}",
    response_model=DocumentUpdateResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        404: {"model": ErrorResponse, "description": "Not Found"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
    summary="文書を更新",
    description="指定されたIDの文書のメタデータを更新します。",
)
async def update_document(
    document_id: str,
    request: DocumentUpdateRequest,
    use_case: UpdateDocumentUseCase = Depends(get_update_document_use_case),
) -> DocumentUpdateResponse:
    """文書を更新する。

    Args:
        document_id: 文書ID
        request: 更新リクエスト
        use_case: 文書更新ユースケース

    Returns:
        文書更新レスポンス

    Raises:
        HTTPException: エラーが発生した場合
    """
    try:
        # 入力DTOを作成
        input_dto = UpdateDocumentInput(
            document_id=document_id,
            title=request.title,
            category=request.category,
            tags=request.tags,
            author=request.author,
            description=request.description,
        )

        # ユースケースを実行
        output_dto = await use_case.execute(input_dto)

        # レスポンスを作成
        return DocumentUpdateResponse(
            document_id=output_dto.document_id,
            title=output_dto.title,
            file_name=output_dto.file_name,
            file_size=output_dto.file_size,
            content_type=output_dto.content_type,
            category=output_dto.category,
            tags=output_dto.tags,
            author=output_dto.author,
            description=output_dto.description,
            created_at=output_dto.created_at,
            updated_at=output_dto.updated_at,
            version=output_dto.version,
        )

    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id '{document_id}' not found",
        ) from None
    except DocumentValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update document: {str(e)}",
        ) from e


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"model": ErrorResponse, "description": "Not Found"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
    summary="文書を削除",
    description="指定されたIDの文書を削除します。",
)
async def delete_document(
    document_id: str,
    use_case: DeleteDocumentUseCase = Depends(get_delete_document_use_case),
) -> None:
    """文書を削除する。

    Args:
        document_id: 文書ID
        use_case: 文書削除ユースケース

    Raises:
        HTTPException: エラーが発生した場合
    """
    try:
        # 入力DTOを作成
        input_dto = DeleteDocumentInput(document_id=document_id)

        # ユースケースを実行
        await use_case.execute(input_dto)

    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id '{document_id}' not found",
        ) from None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}",
        ) from e
