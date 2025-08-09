"""埋め込み関連の依存性注入。"""

from functools import lru_cache

from ....application.use_cases.generate_embeddings import GenerateEmbeddingsUseCase
from ....domain.externals import EmbeddingService
from ....domain.repositories import DocumentRepository
from ....infrastructure.config.settings import get_settings
from ....infrastructure.externals.embeddings import (
    EmbeddingServiceFactory,
)
from ....infrastructure.repositories import DocumentRepositoryImpl
from ...dependencies import get_db_session


@lru_cache
def get_embedding_service() -> EmbeddingService:
    """埋め込みサービスを取得する。

    Returns:
        埋め込みサービスの実装
    """
    settings = get_settings()

    # 埋め込みプロバイダーに応じてサービスを作成
    from typing import Literal, cast

    provider = settings.embedding_provider
    if provider not in ["openai", "ollama", "mock"]:
        provider = "mock"  # デフォルトはmock

    return EmbeddingServiceFactory.create(
        provider=cast(Literal["openai", "ollama", "mock"], provider),
        api_key=settings.openai_api_key,
        model=(
            settings.openai_embedding_model
            if provider == "openai"
            else settings.ollama_embedding_model if provider == "ollama" else None
        ),
        base_url=settings.ollama_base_url if provider == "ollama" else None,
    )


async def get_generate_embeddings_use_case() -> GenerateEmbeddingsUseCase:
    """埋め込み生成ユースケースを取得する。

    Returns:
        埋め込み生成ユースケース
    """
    from ....infrastructure.externals.file_storage import FileStorageService

    db_session = await anext(get_db_session())
    settings = get_settings()
    file_storage = FileStorageService(base_path=settings.file_storage_path)
    document_repository: DocumentRepository = DocumentRepositoryImpl(
        db_session, file_storage
    )
    embedding_service = get_embedding_service()

    return GenerateEmbeddingsUseCase(
        document_repository=document_repository,
        embedding_service=embedding_service,
    )
