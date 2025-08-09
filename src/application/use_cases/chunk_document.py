"""文書チャンク化ユースケース。

文書からテキストを抽出し、チャンクに分割するユースケース。
"""

from ...domain.externals import ChunkingStrategy, EmbeddingService, TextExtractor
from ...domain.repositories import DocumentRepository
from ...domain.services import ChunkingService
from ...domain.value_objects import DocumentId


class ChunkDocumentInput:
    """文書チャンク化の入力DTO。"""

    def __init__(
        self,
        document_id: str,
        chunk_size: int = 1000,
        overlap_size: int = 200,
        generate_embeddings: bool = True,
    ) -> None:
        """初期化する。

        Args:
            document_id: チャンク化対象の文書ID
            chunk_size: チャンクサイズ（文字数）
            overlap_size: 重複サイズ（文字数）
            generate_embeddings: チャンク作成時に埋め込みを生成するかどうか
        """
        self.document_id = document_id
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size
        self.generate_embeddings = generate_embeddings


class ChunkDocumentOutput:
    """文書チャンク化の出力DTO。"""

    def __init__(
        self,
        document_id: str,
        chunk_count: int,
        total_characters: int,
        embeddings_generated: int = 0,
        status: str = "success",
    ) -> None:
        """初期化する。

        Args:
            document_id: 文書ID
            chunk_count: 生成されたチャンク数
            total_characters: 抽出されたテキストの総文字数
            embeddings_generated: 生成された埋め込み数
            status: 処理ステータス（success/failed）
        """
        self.document_id = document_id
        self.chunk_count = chunk_count
        self.total_characters = total_characters
        self.embeddings_generated = embeddings_generated
        self.status = status


class ChunkDocumentUseCase:
    """文書チャンク化ユースケース。

    文書からテキストを抽出し、チャンクに分割して保存する。
    """

    def __init__(
        self,
        document_repository: DocumentRepository,
        text_extractor: TextExtractor,
        chunking_strategy: ChunkingStrategy,
        chunking_service: ChunkingService,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        """初期化する。

        Args:
            document_repository: 文書リポジトリ
            text_extractor: テキスト抽出サービス
            chunking_strategy: チャンク分割戦略
            chunking_service: チャンク化ドメインサービス
            embedding_service: 埋め込みサービス（オプション）
        """
        self._document_repository = document_repository
        self._text_extractor = text_extractor
        self._chunking_strategy = chunking_strategy
        self._chunking_service = chunking_service
        self._embedding_service = embedding_service

    async def execute(self, input_dto: ChunkDocumentInput) -> ChunkDocumentOutput:
        """文書をチャンク化する。

        Args:
            input_dto: チャンク化情報

        Returns:
            チャンク化結果

        Raises:
            ValueError: 文書が見つからない場合
            Exception: 処理中にエラーが発生した場合
        """
        # 文書を取得
        document_id = DocumentId(value=input_dto.document_id)
        document = await self._document_repository.find_by_id(document_id)

        if not document:
            raise ValueError(f"Document not found: {input_dto.document_id}")

        try:
            # テキストを抽出
            extracted_text = await self._text_extractor.extract_text(
                content=document.content,
                content_type=document.metadata.content_type,
            )

            # テキストが空の場合
            if extracted_text.is_empty:
                return ChunkDocumentOutput(
                    document_id=input_dto.document_id,
                    chunk_count=0,
                    total_characters=0,
                    status="success",
                )

            # チャンクを生成
            chunks = self._chunking_service.create_chunks(
                document=document,
                text=extracted_text.content,
                strategy=self._chunking_strategy,
                chunk_size=input_dto.chunk_size,
                overlap_size=input_dto.overlap_size,
            )

            # 文書のチャンクを更新
            self._chunking_service.update_document_chunks(document, chunks)

            # 埋め込みを生成（有効かつサービスが設定されている場合）
            embeddings_generated = 0
            if input_dto.generate_embeddings and self._embedding_service and chunks:
                try:
                    # チャンクのテキストリストを作成
                    texts = [chunk.content for chunk in chunks]

                    # バッチで埋め込みを生成
                    embedding_results = (
                        await self._embedding_service.generate_batch_embeddings(texts)
                    )

                    # 埋め込みをチャンクに設定
                    for i, (chunk, result) in enumerate(
                        zip(chunks, embedding_results, strict=False)
                    ):
                        chunks[i] = chunk.with_embedding(result.embedding)
                        embeddings_generated += 1

                    # 更新されたチャンクで文書を更新
                    self._chunking_service.update_document_chunks(document, chunks)

                except Exception as e:
                    # 埋め込み生成のエラーはログに記録するが、チャンク化は成功とする
                    print(f"Failed to generate embeddings: {str(e)}")

            # 文書を保存
            await self._document_repository.save(document)

            return ChunkDocumentOutput(
                document_id=input_dto.document_id,
                chunk_count=len(chunks),
                total_characters=extracted_text.char_count,
                embeddings_generated=embeddings_generated,
                status="success",
            )

        except Exception as e:
            # エラーログを出力（本番環境ではロギングサービスを使用）
            print(f"Failed to chunk document {input_dto.document_id}: {str(e)}")

            # エラーでも結果を返す
            return ChunkDocumentOutput(
                document_id=input_dto.document_id,
                chunk_count=0,
                total_characters=0,
                status="failed",
            )
