"""FastAPIの依存性注入設定。"""

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..application.use_cases.chunk_document import ChunkDocumentUseCase
from ..application.use_cases.delete_document import DeleteDocumentUseCase
from ..application.use_cases.get_document import GetDocumentUseCase
from ..application.use_cases.get_document_list import GetDocumentListUseCase
from ..application.use_cases.rag import (
    BuildRAGContextUseCase,
    GenerateRAGAnswerUseCase,
    ProcessRAGQueryUseCase,
)
from ..application.use_cases.search_documents import SearchDocumentsUseCase
from ..application.use_cases.update_document import UpdateDocumentUseCase
from ..application.use_cases.upload_document import UploadDocumentUseCase
from ..domain.externals import LLMService, RAGService
from ..domain.repositories import VectorSearchRepository
from ..domain.services import ChunkingService
from ..infrastructure.config.settings import get_settings
from ..infrastructure.database.connection import async_session_factory
from ..infrastructure.externals import FileStorageService
from ..infrastructure.externals.chunking_strategies import (
    JapaneseChunkingStrategy,
    SimpleChunkingStrategy,
)
from ..infrastructure.externals.llms import LLMServiceFactory
from ..infrastructure.externals.rag import RAGServiceImpl
from ..infrastructure.externals.text_extractors import CompositeTextExtractor
from ..infrastructure.repositories import (
    DocumentRepositoryImpl,
    PgVectorRepositoryImpl,
    SessionRepositoryImpl,
    UserRepositoryImpl,
)


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


async def get_vector_search_repository(
    session: AsyncSession = Depends(get_db_session),
) -> VectorSearchRepository | None:
    """ベクトル検索リポジトリを取得する。

    Args:
        session: データベースセッション

    Returns:
        VectorSearchRepository: ベクトル検索リポジトリ（PostgreSQL使用時）
        None: SQLite使用時
    """
    settings = get_settings()

    # PostgreSQLの場合のみPgVectorRepositoryを返す
    if "postgresql" in settings.database_url:
        return PgVectorRepositoryImpl(session)

    # SQLiteの場合はモックを返す（開発用）
    from ..infrastructure.repositories.mock_vector_repository import (
        MockVectorSearchRepository,
    )

    return MockVectorSearchRepository()


async def get_chunk_document_use_case(
    document_repository: DocumentRepositoryImpl = Depends(get_document_repository),
    vector_search_repository: VectorSearchRepository | None = Depends(
        get_vector_search_repository
    ),
) -> ChunkDocumentUseCase:
    """文書チャンク化ユースケースを取得する。

    Args:
        document_repository: 文書リポジトリ
        vector_search_repository: ベクトル検索リポジトリ（オプション）

    Returns:
        ChunkDocumentUseCase: 文書チャンク化ユースケース
    """
    settings = get_settings()

    # 複合テキスト抽出器を作成（自動的に適切な抽出器を選択）
    text_extractor = CompositeTextExtractor()

    # 設定に基づいてチャンク化戦略を選択
    from ..domain.externals import ChunkingStrategy

    chunking_strategy: ChunkingStrategy
    if settings.chunking_strategy == "japanese":
        chunking_strategy = JapaneseChunkingStrategy()
    else:
        chunking_strategy = SimpleChunkingStrategy()

    # チャンク化サービスを作成
    chunking_service = ChunkingService()

    # 埋め込みサービスを取得（設定で有効な場合）
    from ..infrastructure.externals.embeddings import EmbeddingServiceFactory

    embedding_service = None
    if settings.auto_generate_embeddings:
        provider = settings.embedding_provider
        if provider not in ["openai", "ollama", "mock"]:
            provider = "mock"

        embedding_service = EmbeddingServiceFactory.create(
            provider=provider,  # type: ignore[arg-type]
            api_key=settings.openai_api_key,
            model=(
                settings.openai_embedding_model
                if provider == "openai"
                else settings.ollama_embedding_model if provider == "ollama" else None
            ),
            base_url=settings.ollama_base_url if provider == "ollama" else None,
        )

    return ChunkDocumentUseCase(
        document_repository=document_repository,
        text_extractor=text_extractor,
        chunking_strategy=chunking_strategy,
        chunking_service=chunking_service,
        embedding_service=embedding_service,
        vector_search_repository=vector_search_repository,
    )


async def get_upload_document_use_case(
    document_repository: DocumentRepositoryImpl = Depends(get_document_repository),
    file_storage_service: FileStorageService = Depends(get_file_storage_service),
    chunk_document_use_case: ChunkDocumentUseCase = Depends(
        get_chunk_document_use_case
    ),
) -> UploadDocumentUseCase:
    """文書アップロードユースケースを取得する。

    Args:
        document_repository: 文書リポジトリ
        file_storage_service: ファイルストレージサービス
        chunk_document_use_case: 文書チャンク化ユースケース

    Returns:
        UploadDocumentUseCase: 文書アップロードユースケース
    """
    settings = get_settings()

    # 自動チャンク化が無効の場合はNoneを渡す
    chunk_use_case: ChunkDocumentUseCase | None = chunk_document_use_case
    if not settings.enable_auto_chunking:
        chunk_use_case = None

    return UploadDocumentUseCase(
        document_repository=document_repository,
        file_storage_service=file_storage_service,
        chunk_document_use_case=chunk_use_case,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
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


async def get_search_documents_use_case(
    document_repository: DocumentRepositoryImpl = Depends(get_document_repository),
    vector_search_repository: VectorSearchRepository = Depends(
        get_vector_search_repository
    ),
) -> SearchDocumentsUseCase:
    """文書検索ユースケースを取得する。

    Args:
        document_repository: 文書リポジトリ
        vector_search_repository: ベクトル検索リポジトリ

    Returns:
        SearchDocumentsUseCase: 文書検索ユースケース
    """
    # 埋め込みサービスを取得（embeddings依存性モジュールから）
    from .api.dependencies.embeddings import get_embedding_service

    embedding_service = get_embedding_service()

    return SearchDocumentsUseCase(
        document_repository=document_repository,
        vector_search_repository=vector_search_repository,
        embedding_service=embedding_service,
    )


async def get_user_repository(
    session: AsyncSession = Depends(get_db_session),
) -> UserRepositoryImpl:
    """ユーザーリポジトリを取得する。

    Args:
        session: データベースセッション

    Returns:
        UserRepositoryImpl: ユーザーリポジトリ
    """
    return UserRepositoryImpl(session=session)


async def get_session_repository(
    session: AsyncSession = Depends(get_db_session),
) -> SessionRepositoryImpl:
    """セッションリポジトリを取得する。

    Args:
        session: データベースセッション

    Returns:
        SessionRepositoryImpl: セッションリポジトリ
    """
    return SessionRepositoryImpl(session=session)


def get_llm_service() -> LLMService:
    """LLMサービスを取得する。

    Returns:
        LLMService: LLMサービス
    """
    settings = get_settings()
    return LLMServiceFactory.from_settings(settings)


def get_rag_service(
    llm_service: LLMService = Depends(get_llm_service),
) -> RAGService:
    """RAGサービスを取得する。

    Args:
        llm_service: LLMサービス

    Returns:
        RAGService: RAGサービス
    """
    return RAGServiceImpl(llm_service=llm_service)


async def get_build_rag_context_use_case(
    document_repository: DocumentRepositoryImpl = Depends(get_document_repository),
) -> BuildRAGContextUseCase:
    """RAGコンテキスト構築ユースケースを取得する。

    Args:
        document_repository: 文書リポジトリ

    Returns:
        BuildRAGContextUseCase: RAGコンテキスト構築ユースケース
    """
    return BuildRAGContextUseCase(document_repository=document_repository)


async def get_generate_rag_answer_use_case(
    llm_service: LLMService = Depends(get_llm_service),
    rag_service: RAGService = Depends(get_rag_service),
) -> GenerateRAGAnswerUseCase:
    """RAG回答生成ユースケースを取得する。

    Args:
        llm_service: LLMサービス
        rag_service: RAGサービス

    Returns:
        GenerateRAGAnswerUseCase: RAG回答生成ユースケース
    """
    return GenerateRAGAnswerUseCase(
        llm_service=llm_service,
        rag_service=rag_service,
    )


def get_process_rag_query_use_case(
    search_use_case: SearchDocumentsUseCase = Depends(get_search_documents_use_case),
    build_context_use_case: BuildRAGContextUseCase = Depends(
        get_build_rag_context_use_case
    ),
    generate_answer_use_case: GenerateRAGAnswerUseCase = Depends(
        get_generate_rag_answer_use_case
    ),
    rag_service: RAGService = Depends(get_rag_service),
) -> ProcessRAGQueryUseCase:
    """RAGクエリ処理ユースケースを取得する。

    Args:
        search_use_case: 文書検索ユースケース
        build_context_use_case: コンテキスト構築ユースケース
        generate_answer_use_case: 回答生成ユースケース
        rag_service: RAGサービス

    Returns:
        ProcessRAGQueryUseCase: RAGクエリ処理ユースケース
    """
    return ProcessRAGQueryUseCase(
        search_use_case=search_use_case,
        build_context_use_case=build_context_use_case,
        generate_answer_use_case=generate_answer_use_case,
        rag_service=rag_service,
    )
