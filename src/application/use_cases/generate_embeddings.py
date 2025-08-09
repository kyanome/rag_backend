"""埋め込みベクトル生成ユースケース。

文書チャンクから埋め込みベクトルを生成するユースケース。
"""

from ...domain.externals import EmbeddingService
from ...domain.repositories import DocumentRepository, VectorSearchRepository
from ...domain.value_objects import DocumentId


class GenerateEmbeddingsInput:
    """埋め込みベクトル生成の入力DTO。"""

    def __init__(
        self,
        document_id: str,
        regenerate: bool = False,
        store_in_vector_db: bool = True,
    ) -> None:
        """初期化する。

        Args:
            document_id: 埋め込みを生成する文書ID
            regenerate: 既存の埋め込みを再生成するかどうか
            store_in_vector_db: ベクトルDBに保存するかどうか
        """
        self.document_id = document_id
        self.regenerate = regenerate
        self.store_in_vector_db = store_in_vector_db


class GenerateEmbeddingsOutput:
    """埋め込みベクトル生成の出力DTO。"""

    def __init__(
        self,
        document_id: str,
        chunk_count: int,
        embeddings_generated: int,
        embeddings_skipped: int,
        embeddings_stored: int,
        embedding_model: str,
        embedding_dimensions: int,
        status: str,
        vector_storage_status: str = "not_attempted",
    ) -> None:
        """初期化する。

        Args:
            document_id: 文書ID
            chunk_count: 総チャンク数
            embeddings_generated: 生成された埋め込み数
            embeddings_skipped: スキップされた埋め込み数
            embeddings_stored: ベクトルDBに保存された埋め込み数
            embedding_model: 使用されたモデル名
            embedding_dimensions: 埋め込みベクトルの次元数
            status: 処理ステータス（success/partial/failed）
            vector_storage_status: ベクトル保存ステータス（success/partial/failed/not_attempted）
        """
        self.document_id = document_id
        self.chunk_count = chunk_count
        self.embeddings_generated = embeddings_generated
        self.embeddings_skipped = embeddings_skipped
        self.embeddings_stored = embeddings_stored
        self.embedding_model = embedding_model
        self.embedding_dimensions = embedding_dimensions
        self.status = status
        self.vector_storage_status = vector_storage_status


class GenerateEmbeddingsUseCase:
    """埋め込みベクトル生成ユースケース。

    文書のチャンクから埋め込みベクトルを生成して保存する。
    オプションでベクトルDBへの保存も行う。
    """

    def __init__(
        self,
        document_repository: DocumentRepository,
        embedding_service: EmbeddingService,
        vector_search_repository: VectorSearchRepository | None = None,
    ) -> None:
        """初期化する。

        Args:
            document_repository: 文書リポジトリ
            embedding_service: 埋め込みサービス
            vector_search_repository: ベクトル検索リポジトリ（オプション）
        """
        self._document_repository = document_repository
        self._embedding_service = embedding_service
        self._vector_search_repository = vector_search_repository

    async def execute(
        self, input_dto: GenerateEmbeddingsInput
    ) -> GenerateEmbeddingsOutput:
        """文書チャンクの埋め込みベクトルを生成する。

        Args:
            input_dto: 埋め込み生成情報

        Returns:
            埋め込み生成結果

        Raises:
            ValueError: 文書が見つからない場合
            Exception: 処理中にエラーが発生した場合
        """
        # 文書を取得
        document_id = DocumentId(value=input_dto.document_id)
        document = await self._document_repository.find_by_id(document_id)

        if not document:
            raise ValueError(f"Document not found: {input_dto.document_id}")

        # チャンクがない場合
        if not document.chunks:
            return GenerateEmbeddingsOutput(
                document_id=input_dto.document_id,
                chunk_count=0,
                embeddings_generated=0,
                embeddings_skipped=0,
                embeddings_stored=0,
                embedding_model=self._embedding_service.get_model_name(),
                embedding_dimensions=self._embedding_service.get_dimensions(),
                status="success",
                vector_storage_status="not_attempted",
            )

        # 埋め込みを生成するチャンクを選択
        chunks_to_process = []
        chunks_skipped = 0

        for chunk in document.chunks:
            # 再生成フラグがない場合、既に埋め込みがあればスキップ
            if not input_dto.regenerate and chunk.has_embedding:
                chunks_skipped += 1
                continue
            chunks_to_process.append(chunk)

        # 処理するチャンクがない場合
        if not chunks_to_process:
            return GenerateEmbeddingsOutput(
                document_id=input_dto.document_id,
                chunk_count=len(document.chunks),
                embeddings_generated=0,
                embeddings_skipped=chunks_skipped,
                embeddings_stored=0,
                embedding_model=self._embedding_service.get_model_name(),
                embedding_dimensions=self._embedding_service.get_dimensions(),
                status="success",
                vector_storage_status="not_attempted",
            )

        try:
            # バッチで埋め込みを生成
            texts = [chunk.content for chunk in chunks_to_process]
            embedding_results = await self._embedding_service.generate_batch_embeddings(
                texts
            )

            # 埋め込みをチャンクに設定
            embeddings_generated = 0
            chunk_embeddings = []  # ベクトルDB保存用

            for chunk, result in zip(
                chunks_to_process, embedding_results, strict=False
            ):
                # チャンクに埋め込みを設定（新しいインスタンスを作成）
                updated_chunk = chunk.with_embedding(result.embedding)
                # 文書のチャンクリストを更新
                for i, doc_chunk in enumerate(document.chunks):
                    if doc_chunk.id == chunk.id:
                        document.chunks[i] = updated_chunk
                        embeddings_generated += 1
                        # ベクトルDB保存用のリストに追加
                        chunk_embeddings.append((chunk.id, result.embedding))
                        break

            # 文書を保存
            await self._document_repository.save(document)

            # ベクトルDBに保存（有効かつリポジトリが設定されている場合）
            embeddings_stored = 0
            vector_storage_status = "not_attempted"

            if (
                input_dto.store_in_vector_db
                and self._vector_search_repository
                and chunk_embeddings
            ):
                try:
                    # バッチで保存
                    await self._vector_search_repository.save_chunk_embeddings_batch(
                        chunk_embeddings
                    )
                    embeddings_stored = len(chunk_embeddings)
                    vector_storage_status = "success"
                except Exception as e:
                    # ベクトルDB保存のエラーはログに記録するが、埋め込み生成は成功とする
                    print(f"Failed to store embeddings in vector DB: {str(e)}")
                    vector_storage_status = "failed"

            # ステータスを決定
            status = "success"
            if embeddings_generated < len(chunks_to_process):
                status = "partial"

            return GenerateEmbeddingsOutput(
                document_id=input_dto.document_id,
                chunk_count=len(document.chunks),
                embeddings_generated=embeddings_generated,
                embeddings_skipped=chunks_skipped,
                embeddings_stored=embeddings_stored,
                embedding_model=self._embedding_service.get_model_name(),
                embedding_dimensions=self._embedding_service.get_dimensions(),
                status=status,
                vector_storage_status=vector_storage_status,
            )

        except Exception as e:
            # エラーログを出力（本番環境ではロギングサービスを使用）
            print(
                f"Failed to generate embeddings for document {input_dto.document_id}: {str(e)}"
            )

            # エラーでも部分的な結果を返す
            return GenerateEmbeddingsOutput(
                document_id=input_dto.document_id,
                chunk_count=len(document.chunks),
                embeddings_generated=0,
                embeddings_skipped=chunks_skipped,
                embeddings_stored=0,
                embedding_model=self._embedding_service.get_model_name(),
                embedding_dimensions=self._embedding_service.get_dimensions(),
                status="failed",
                vector_storage_status="not_attempted",
            )
