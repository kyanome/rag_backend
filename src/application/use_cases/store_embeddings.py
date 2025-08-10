"""埋め込みベクトル保存ユースケース。

生成された埋め込みベクトルをベクトルストレージに保存する。
DDDの原則に従い、ドメイン層のインターフェースのみに依存。
"""

import asyncio

from ...domain.exceptions.vector_storage_exceptions import (
    VectorStorageError,
)
from ...domain.repositories import DocumentRepository, VectorSearchRepository
from ...domain.value_objects import DocumentId


class StoreEmbeddingsInput:
    """埋め込みベクトル保存の入力DTO。"""

    def __init__(
        self,
        document_id: str,
        chunk_embeddings: list[tuple[str, list[float]]],
        batch_size: int = 100,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        """初期化する。

        Args:
            document_id: 文書ID
            chunk_embeddings: (chunk_id, embedding)のタプルのリスト
            batch_size: バッチサイズ
            max_retries: 最大リトライ回数
            retry_delay: リトライ間隔（秒）
        """
        self.document_id = document_id
        self.chunk_embeddings = chunk_embeddings
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay


class StoreEmbeddingsOutput:
    """埋め込みベクトル保存の出力DTO。"""

    def __init__(
        self,
        document_id: str,
        total_chunks: int,
        stored_count: int,
        failed_count: int,
        status: str,
        failed_chunk_ids: list[str] | None = None,
    ) -> None:
        """初期化する。

        Args:
            document_id: 文書ID
            total_chunks: 総チャンク数
            stored_count: 保存成功数
            failed_count: 保存失敗数
            status: 処理ステータス（success/partial/failed）
            failed_chunk_ids: 失敗したチャンクIDのリスト
        """
        self.document_id = document_id
        self.total_chunks = total_chunks
        self.stored_count = stored_count
        self.failed_count = failed_count
        self.status = status
        self.failed_chunk_ids = failed_chunk_ids or []


class StoreEmbeddingsUseCase:
    """埋め込みベクトル保存ユースケース。

    生成された埋め込みベクトルをベクトルストレージに保存する。
    バッチ処理とリトライ機構を含む。
    """

    def __init__(
        self,
        document_repository: DocumentRepository,
        vector_search_repository: VectorSearchRepository,
    ) -> None:
        """初期化する。

        Args:
            document_repository: 文書リポジトリ
            vector_search_repository: ベクトル検索リポジトリ
        """
        self._document_repository = document_repository
        self._vector_search_repository = vector_search_repository

    async def execute(self, input_dto: StoreEmbeddingsInput) -> StoreEmbeddingsOutput:
        """埋め込みベクトルを保存する。

        Args:
            input_dto: 保存情報

        Returns:
            保存結果

        Raises:
            ValueError: 文書が見つからない場合
        """
        # 文書の存在確認
        document_id = DocumentId(value=input_dto.document_id)
        document = await self._document_repository.find_by_id(document_id)

        if not document:
            raise ValueError(f"Document not found: {input_dto.document_id}")

        # 空の場合は即座に成功を返す
        if not input_dto.chunk_embeddings:
            return StoreEmbeddingsOutput(
                document_id=input_dto.document_id,
                total_chunks=0,
                stored_count=0,
                failed_count=0,
                status="success",
            )

        # バッチに分割して処理
        batches = self._create_batches(input_dto.chunk_embeddings, input_dto.batch_size)

        stored_count = 0
        failed_chunk_ids = []

        for batch in batches:
            success = await self._store_batch_with_retry(
                batch, input_dto.max_retries, input_dto.retry_delay
            )

            if success:
                stored_count += len(batch)
            else:
                # 失敗したチャンクIDを記録
                failed_chunk_ids.extend([chunk_id for chunk_id, _ in batch])

        # ステータスを決定
        failed_count = len(failed_chunk_ids)
        if failed_count == 0:
            status = "success"
        elif stored_count > 0:
            status = "partial"
        else:
            status = "failed"

        return StoreEmbeddingsOutput(
            document_id=input_dto.document_id,
            total_chunks=len(input_dto.chunk_embeddings),
            stored_count=stored_count,
            failed_count=failed_count,
            status=status,
            failed_chunk_ids=failed_chunk_ids,
        )

    def _create_batches(
        self,
        chunk_embeddings: list[tuple[str, list[float]]],
        batch_size: int,
    ) -> list[list[tuple[str, list[float]]]]:
        """チャンク埋め込みをバッチに分割する。

        Args:
            chunk_embeddings: チャンク埋め込みのリスト
            batch_size: バッチサイズ

        Returns:
            バッチのリスト
        """
        batches = []
        for i in range(0, len(chunk_embeddings), batch_size):
            batch = chunk_embeddings[i : i + batch_size]
            batches.append(batch)
        return batches

    async def _store_batch_with_retry(
        self,
        batch: list[tuple[str, list[float]]],
        max_retries: int,
        retry_delay: float,
    ) -> bool:
        """バッチをリトライ付きで保存する。

        指数バックオフによるリトライを実装。

        Args:
            batch: 保存するバッチ
            max_retries: 最大リトライ回数
            retry_delay: 初期リトライ遅延（秒）

        Returns:
            成功した場合True
        """
        for attempt in range(max_retries):
            try:
                # タイムアウト付きで保存を実行
                await asyncio.wait_for(
                    self._vector_search_repository.save_chunk_embeddings_batch(batch),
                    timeout=30.0,  # 30秒のタイムアウト
                )
                return True

            except TimeoutError:
                # タイムアウトエラー
                if attempt < max_retries - 1:
                    # 指数バックオフ
                    wait_time = retry_delay * (2**attempt)
                    print(
                        f"Timeout storing batch, retrying in {wait_time}s "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    print(
                        f"Failed to store batch after {max_retries} attempts (timeout)"
                    )
                    return False

            except VectorStorageError as e:
                # ベクトルストレージ固有のエラー
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2**attempt)
                    print(
                        f"Vector storage error: {str(e)}, retrying in {wait_time}s "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    print(
                        f"Failed to store batch after {max_retries} attempts: {str(e)}"
                    )
                    return False

            except Exception as e:
                # その他のエラーは即座に失敗
                print(f"Unexpected error storing batch: {str(e)}")
                return False

        return False
