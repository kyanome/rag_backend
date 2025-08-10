"""RAGコンテキスト構築ユースケース。

検索結果からRAGコンテキストを構築するユースケースを実装する。
"""

from typing import Any

from ....domain.repositories import DocumentRepository
from ....domain.value_objects import DocumentId, SearchResultItem
from ....domain.value_objects.rag_context import RAGContext


class BuildRAGContextUseCase:
    """RAGコンテキスト構築ユースケース。

    検索結果からLLMに渡すコンテキストを構築する。
    """

    def __init__(
        self,
        document_repository: DocumentRepository,
        max_context_length: int = 4000,
        include_metadata: bool = True,
    ) -> None:
        """ユースケースを初期化する。

        Args:
            document_repository: 文書リポジトリ
            max_context_length: コンテキストの最大文字数
            include_metadata: メタデータを含めるかどうか
        """
        self._document_repository = document_repository
        self._max_context_length = max_context_length
        self._include_metadata = include_metadata

    async def execute(
        self,
        query_text: str,
        search_results: list[Any],
    ) -> RAGContext:
        """RAGコンテキストを構築する。

        Args:
            query_text: クエリテキスト
            search_results: 検索結果のリスト（SearchResultItemOutputのリスト）

        Returns:
            構築されたRAGコンテキスト

        Raises:
            Exception: コンテキスト構築中にエラーが発生した場合
        """
        try:
            # SearchResultItemに変換
            search_result_items = []
            for result in search_results:
                # DTOからドメインモデルに変換
                item = SearchResultItem(
                    document_id=DocumentId(value=result.document_id),
                    document_title=result.document_title,
                    content_preview=result.content_preview,
                    score=result.score,
                    match_type=result.match_type,
                    chunk_id=result.chunk_id,
                    chunk_index=result.chunk_index,
                    highlights=(
                        result.highlights if hasattr(result, "highlights") else []
                    ),
                )
                search_result_items.append(item)

            # 重複除去とランキング
            deduplicated_results = self._deduplicate_results(search_result_items)

            # コンテキストを構築
            context = RAGContext.from_search_results(
                query_text=query_text,
                search_results=deduplicated_results,
                max_context_length=self._max_context_length,
            )

            # メタデータを追加
            if self._include_metadata:
                context = self._enrich_with_metadata(context)

            return context

        except Exception as e:
            raise Exception(f"Failed to build RAG context: {e}") from e

    def _deduplicate_results(
        self, results: list[SearchResultItem]
    ) -> list[SearchResultItem]:
        """検索結果の重複を除去する。

        同じ文書の複数のチャンクがある場合、最も関連性の高いものを選択する。

        Args:
            results: 検索結果のリスト

        Returns:
            重複を除去した検索結果のリスト
        """
        # 文書IDごとに最高スコアのチャンクを保持
        best_chunks: dict[str, SearchResultItem] = {}

        for result in results:
            doc_id = result.document_id.value

            # チャンクがある場合は、チャンクごとの最高スコアを保持
            if result.chunk_id:
                chunk_key = f"{doc_id}_{result.chunk_id}"
                if (
                    chunk_key not in best_chunks
                    or result.score > best_chunks[chunk_key].score
                ):
                    best_chunks[chunk_key] = result
            else:
                # チャンクがない場合は文書レベルでの重複除去
                if (
                    doc_id not in best_chunks
                    or result.score > best_chunks[doc_id].score
                ):
                    best_chunks[doc_id] = result

        # スコアでソートして返す
        return sorted(
            best_chunks.values(),
            key=lambda x: x.score,
            reverse=True,
        )

    def _enrich_with_metadata(self, context: RAGContext) -> RAGContext:
        """コンテキストにメタデータを追加する。

        Args:
            context: RAGコンテキスト

        Returns:
            メタデータが追加されたコンテキスト
        """
        # メタデータを辞書に追加
        metadata = dict(context.metadata)
        metadata.update(
            {
                "deduplication_applied": True,
                "max_context_length": self._max_context_length,
                "context_truncated": len(context.context_text)
                >= self._max_context_length - 10,
                "document_titles": context.get_document_titles(),
                "top_score": context.max_relevance_score,
            }
        )

        # 新しいコンテキストを作成（Pydanticのfrozenモデルのため）
        return RAGContext(
            query_text=context.query_text,
            search_results=context.search_results,
            context_text=context.context_text,
            total_chunks=context.total_chunks,
            unique_documents=context.unique_documents,
            max_relevance_score=context.max_relevance_score,
            metadata=metadata,
        )

    def validate_context(self, context: RAGContext) -> tuple[bool, str]:
        """コンテキストの妥当性を検証する。

        Args:
            context: RAGコンテキスト

        Returns:
            (妥当性フラグ, メッセージ)のタプル
        """
        if not context.search_results:
            return False, "No search results found"

        if not context.is_sufficient():
            return False, "Insufficient context (low relevance or too few results)"

        if len(context.context_text) < 50:
            return False, "Context text is too short"

        return True, "Context is valid"
