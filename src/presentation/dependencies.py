"""FastAPIの依存性注入設定。"""

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..application.use_cases.delete_document import DeleteDocumentUseCase
from ..application.use_cases.get_document import GetDocumentUseCase
from ..application.use_cases.get_document_list import GetDocumentListUseCase
from ..application.use_cases.update_document import UpdateDocumentUseCase
from ..application.use_cases.upload_document import UploadDocumentUseCase
from ..infrastructure.config.settings import get_settings
from ..infrastructure.database.connection import async_session_factory
from ..infrastructure.externals import FileStorageService
from ..infrastructure.repositories import DocumentRepositoryImpl


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """データベースセッションを取得する。

    Yields:
        AsyncSession: データベースセッション
    """
    factory = async_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_file_storage_service() -> FileStorageService:
    """ファイルストレージサービスを取得する。

    Returns:
        FileStorageService: ファイルストレージサービス
    """
    settings = get_settings()
    return FileStorageService(base_path=settings.file_storage_path)


async def get_document_repository(
    session: AsyncSession = Depends(get_db_session),
    file_storage_service: FileStorageService = Depends(get_file_storage_service),
) -> DocumentRepositoryImpl:
    """文書リポジトリを取得する。

    Args:
        session: データベースセッション
        file_storage_service: ファイルストレージサービス

    Returns:
        DocumentRepositoryImpl: 文書リポジトリ
    """
    return DocumentRepositoryImpl(session, file_storage_service)


async def get_upload_document_use_case(
    document_repository: DocumentRepositoryImpl = Depends(get_document_repository),
    file_storage_service: FileStorageService = Depends(get_file_storage_service),
) -> UploadDocumentUseCase:
    """文書アップロードユースケースを取得する。

    Args:
        document_repository: 文書リポジトリ
        file_storage_service: ファイルストレージサービス

    Returns:
        UploadDocumentUseCase: 文書アップロードユースケース
    """
    return UploadDocumentUseCase(
        document_repository=document_repository,
        file_storage_service=file_storage_service,
    )


async def get_get_document_list_use_case(
    document_repository: DocumentRepositoryImpl = Depends(get_document_repository),
) -> GetDocumentListUseCase:
    """文書一覧取得ユースケースを取得する。

    Args:
        document_repository: 文書リポジトリ

    Returns:
        GetDocumentListUseCase: 文書一覧取得ユースケース
    """
    return GetDocumentListUseCase(document_repository=document_repository)


async def get_get_document_use_case(
    document_repository: DocumentRepositoryImpl = Depends(get_document_repository),
) -> GetDocumentUseCase:
    """文書詳細取得ユースケースを取得する。

    Args:
        document_repository: 文書リポジトリ

    Returns:
        GetDocumentUseCase: 文書詳細取得ユースケース
    """
    return GetDocumentUseCase(document_repository=document_repository)


async def get_update_document_use_case(
    document_repository: DocumentRepositoryImpl = Depends(get_document_repository),
) -> UpdateDocumentUseCase:
    """文書更新ユースケースを取得する。

    Args:
        document_repository: 文書リポジトリ

    Returns:
        UpdateDocumentUseCase: 文書更新ユースケース
    """
    return UpdateDocumentUseCase(document_repository=document_repository)


async def get_delete_document_use_case(
    document_repository: DocumentRepositoryImpl = Depends(get_document_repository),
) -> DeleteDocumentUseCase:
    """文書削除ユースケースを取得する。

    Args:
        document_repository: 文書リポジトリ

    Returns:
        DeleteDocumentUseCase: 文書削除ユースケース
    """
    return DeleteDocumentUseCase(document_repository=document_repository)
