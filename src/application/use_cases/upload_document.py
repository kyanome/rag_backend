"""文書アップロードユースケース。"""

from ...domain.entities import Document
from ...domain.repositories import DocumentRepository
from ...domain.value_objects import DocumentId, DocumentMetadata, UserId
from ...infrastructure.externals import FileStorageService
from .chunk_document import ChunkDocumentInput, ChunkDocumentUseCase


class UploadDocumentInput:
    """文書アップロードの入力DTO。"""

    def __init__(
        self,
        file_name: str,
        file_content: bytes,
        file_size: int,
        content_type: str,
        title: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        author: str | None = None,
        description: str | None = None,
        owner_id: UserId | None = None,
    ) -> None:
        """初期化する。

        Args:
            file_name: ファイル名
            file_content: ファイルの内容
            file_size: ファイルサイズ（バイト）
            content_type: コンテンツタイプ（MIME type）
            title: 文書タイトル（省略時はファイル名を使用）
            category: 文書カテゴリ
            tags: タグリスト
            author: 作成者
            description: 文書の説明
            owner_id: 文書の所有者ID
        """
        self.file_name = file_name
        self.file_content = file_content
        self.file_size = file_size
        self.content_type = content_type
        self.title = title or file_name
        self.category = category
        self.tags = tags or []
        self.author = author
        self.description = description
        self.owner_id = owner_id


class UploadDocumentOutput:
    """文書アップロードの出力DTO。"""

    def __init__(
        self,
        document_id: str,
        title: str,
        file_name: str,
        file_size: int,
        content_type: str,
        created_at: str,
        chunk_count: int = 0,
        chunking_status: str = "not_started",
    ) -> None:
        """初期化する。

        Args:
            document_id: 文書ID
            title: 文書タイトル
            file_name: ファイル名
            file_size: ファイルサイズ
            content_type: コンテンツタイプ
            created_at: 作成日時（ISO形式）
            chunk_count: 生成されたチャンク数
            chunking_status: チャンク化ステータス（not_started/success/failed）
        """
        self.document_id = document_id
        self.title = title
        self.file_name = file_name
        self.file_size = file_size
        self.content_type = content_type
        self.created_at = created_at
        self.chunk_count = chunk_count
        self.chunking_status = chunking_status


class UploadDocumentUseCase:
    """文書アップロードユースケース。

    文書のアップロード処理を管理し、ファイルの保存と
    メタデータの登録を行う。
    """

    # サポートするファイル形式
    SUPPORTED_CONTENT_TYPES = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
        "application/msword",  # .doc
        "text/plain",
        "text/csv",
        "text/markdown",
    }

    # 最大ファイルサイズ（100MB）
    MAX_FILE_SIZE = 100 * 1024 * 1024

    def __init__(
        self,
        document_repository: DocumentRepository,
        file_storage_service: FileStorageService,
        chunk_document_use_case: ChunkDocumentUseCase | None = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> None:
        """初期化する。

        Args:
            document_repository: 文書リポジトリ
            file_storage_service: ファイルストレージサービス
            chunk_document_use_case: 文書チャンク化ユースケース（オプション）
            chunk_size: チャンクサイズ（文字数）
            chunk_overlap: チャンク間の重複サイズ（文字数）
        """
        self._document_repository = document_repository
        self._file_storage_service = file_storage_service
        self._chunk_document_use_case = chunk_document_use_case
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    async def execute(self, input_dto: UploadDocumentInput) -> UploadDocumentOutput:
        """文書をアップロードする。

        Args:
            input_dto: アップロード情報

        Returns:
            アップロード結果

        Raises:
            ValueError: 無効な入力の場合
        """
        # 入力検証
        self._validate_input(input_dto)

        # 文書IDを生成
        document_id = DocumentId.generate()

        # ファイルを保存
        await self._file_storage_service.save(
            document_id=str(document_id),
            file_name=input_dto.file_name,
            content=input_dto.file_content,
        )

        # メタデータを作成
        metadata = DocumentMetadata.create_new(
            file_name=input_dto.file_name,
            file_size=input_dto.file_size,
            content_type=input_dto.content_type,
            category=input_dto.category,
            tags=input_dto.tags,
            author=input_dto.author,
            description=input_dto.description,
        )

        # 文書エンティティを作成
        document = Document.create(
            title=input_dto.title,
            content=input_dto.file_content,
            metadata=metadata,
            document_id=document_id,
            owner_id=input_dto.owner_id,
        )

        # 文書を保存
        await self._document_repository.save(document)

        # チャンク化処理を実行（オプション）
        chunk_count = 0
        chunking_status = "not_started"

        if self._chunk_document_use_case:
            try:
                chunk_input = ChunkDocumentInput(
                    document_id=str(document.id),
                    chunk_size=self._chunk_size,
                    overlap_size=self._chunk_overlap,
                )
                chunk_result = await self._chunk_document_use_case.execute(chunk_input)
                chunk_count = chunk_result.chunk_count
                chunking_status = chunk_result.status
            except Exception as e:
                # チャンク化に失敗してもアップロード自体は成功とする
                # 本番環境ではログを出力
                print(f"Failed to chunk document {document.id}: {str(e)}")
                chunking_status = "failed"

        # 出力DTOを作成
        return UploadDocumentOutput(
            document_id=str(document.id),
            title=document.title,
            file_name=metadata.file_name,
            file_size=metadata.file_size,
            content_type=metadata.content_type,
            created_at=metadata.created_at.isoformat(),
            chunk_count=chunk_count,
            chunking_status=chunking_status,
        )

    def _validate_input(self, input_dto: UploadDocumentInput) -> None:
        """入力を検証する。

        Args:
            input_dto: 検証する入力

        Raises:
            ValueError: 検証エラーの場合
        """
        # ファイルサイズチェック
        if input_dto.file_size > self.MAX_FILE_SIZE:
            raise ValueError(
                f"File size exceeds maximum allowed size of {self.MAX_FILE_SIZE} bytes"
            )

        # コンテンツタイプチェック
        if input_dto.content_type not in self.SUPPORTED_CONTENT_TYPES:
            raise ValueError(
                f"Unsupported content type: {input_dto.content_type}. "
                f"Supported types: {', '.join(self.SUPPORTED_CONTENT_TYPES)}"
            )

        # ファイル名チェック
        if not input_dto.file_name or not input_dto.file_name.strip():
            raise ValueError("File name cannot be empty")

        # ファイル内容チェック
        if not input_dto.file_content:
            raise ValueError("File content cannot be empty")
