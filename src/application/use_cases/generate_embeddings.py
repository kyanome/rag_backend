"""埋め込みベクトル生成ユースケース。

文書チャンクから埋め込みベクトルを生成するユースケース。
"""

from ...domain.externals import EmbeddingService
from ...domain.repositories import DocumentRepository
from ...domain.value_objects import DocumentId


class GenerateEmbeddingsInput:
    """埋め込みベクトル生成の入力DTO。"""

    def __init__(
        self,
        document_id: str,
        regenerate: bool = False,
    ) -> None:
        """初期化する。

        Args:
            document_id: 埋め込みを生成する文書ID
            regenerate: 既存の埋め込みを再生成するかどうか
        """
        self.document_id = document_id
        self.regenerate = regenerate


class GenerateEmbeddingsOutput:
    """埋め込みベクトル生成の出力DTO。"""

    def __init__(
        self,
        document_id: str,
        chunk_count: int,
        embeddings_generated: int,
        embeddings_skipped: int,
        embedding_model: str,
        embedding_dimensions: int,
        status: str,
    ) -> None:
        """初期化する。

        Args:
            document_id: 文書ID
            chunk_count: 総チャンク数
            embeddings_generated: 生成された埋め込み数
            embeddings_skipped: スキップされた埋め込み数
            embedding_model: 使用されたモデル名
            embedding_dimensions: 埋め込みベクトルの次元数
            status: 処理ステータス（success/partial/failed）
        """
        self.document_id = document_id
        self.chunk_count = chunk_count
        self.embeddings_generated = embeddings_generated
        self.embeddings_skipped = embeddings_skipped
        self.embedding_model = embedding_model
        self.embedding_dimensions = embedding_dimensions
        self.status = status


class GenerateEmbeddingsUseCase:
    """埋め込みベクトル生成ユースケース。

    文書のチャンクから埋め込みベクトルを生成して保存する。
    """

    def __init__(
        self,
        document_repository: DocumentRepository,
        embedding_service: EmbeddingService,
    ) -> None:
        """初期化する。

        Args:
            document_repository: 文書リポジトリ
            embedding_service: 埋め込みサービス
        """
        self._document_repository = document_repository
        self._embedding_service = embedding_service

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
                embedding_model=self._embedding_service.get_model_name(),
                embedding_dimensions=self._embedding_service.get_dimensions(),
                status="success",
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
                embedding_model=self._embedding_service.get_model_name(),
                embedding_dimensions=self._embedding_service.get_dimensions(),
                status="success",
            )

        try:
            # バッチで埋め込みを生成
            texts = [chunk.content for chunk in chunks_to_process]
            embedding_results = await self._embedding_service.generate_batch_embeddings(
                texts
            )

            # 埋め込みをチャンクに設定
            embeddings_generated = 0
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
                        break

            # 文書を保存
            await self._document_repository.save(document)

            # ステータスを決定
            status = "success"
            if embeddings_generated < len(chunks_to_process):
                status = "partial"

            return GenerateEmbeddingsOutput(
                document_id=input_dto.document_id,
                chunk_count=len(document.chunks),
                embeddings_generated=embeddings_generated,
                embeddings_skipped=chunks_skipped,
                embedding_model=self._embedding_service.get_model_name(),
                embedding_dimensions=self._embedding_service.get_dimensions(),
                status=status,
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
                embedding_model=self._embedding_service.get_model_name(),
                embedding_dimensions=self._embedding_service.get_dimensions(),
                status="failed",
            )
