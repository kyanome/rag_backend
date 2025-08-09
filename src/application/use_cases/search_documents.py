"""文書検索ユースケース。

DDDの原則に従い、キーワード検索、ベクトル検索、ハイブリッド検索を統合する。
"""

import time

from pydantic import BaseModel, Field, field_validator

from ...domain.externals import EmbeddingService
from ...domain.repositories import DocumentRepository, VectorSearchRepository
from ...domain.value_objects import (
    DocumentId,
    SearchQuery,
    SearchResult,
    SearchResultItem,
    SearchType,
)


class SearchDocumentsInput(BaseModel):
    """文書検索の入力DTO。

    Attributes:
        query: 検索クエリ文字列
        search_type: 検索タイプ（keyword/vector/hybrid）
        limit: 返す結果の最大数
        offset: スキップする件数
        similarity_threshold: ベクトル検索の類似度閾値
        document_ids: 検索対象を限定する文書ID（オプション）
    """

    query: str = Field(..., min_length=1, max_length=1000, description="検索クエリ")
    search_type: str = Field(default="hybrid", description="検索タイプ")
    limit: int = Field(default=10, ge=1, le=100, description="結果の最大数")
    offset: int = Field(default=0, ge=0, description="スキップする件数")
    similarity_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0, description="類似度の閾値"
    )
    document_ids: list[str] | None = Field(default=None, description="検索対象の文書ID")

    @field_validator("search_type")
    @classmethod
    def validate_search_type(cls, v: str) -> str:
        """検索タイプの妥当性を検証する。"""
        valid_types = ["keyword", "vector", "hybrid"]
        if v not in valid_types:
            raise ValueError(f"search_type must be one of {valid_types}")
        return v

    def to_domain(self) -> SearchQuery:
        """ドメインのSearchQueryに変換する。

        Returns:
            SearchQuery値オブジェクト
        """
        return SearchQuery(
            query_text=self.query.strip(),
            search_type=SearchType(self.search_type),
            limit=self.limit,
            offset=self.offset,
            similarity_threshold=self.similarity_threshold,
            filters={"document_ids": self.document_ids} if self.document_ids else None,
        )


class SearchResultItemOutput(BaseModel):
    """検索結果アイテムの出力DTO。

    Attributes:
        document_id: 文書ID
        document_title: 文書タイトル
        content_preview: 内容のプレビュー
        score: 関連性スコア（0.0〜1.0）
        match_type: マッチタイプ（keyword/vector/both）
        confidence_level: 信頼度レベル（high/medium/low）
        chunk_id: チャンクID（ベクトル検索の場合）
        chunk_index: チャンクインデックス（ベクトル検索の場合）
        highlights: ハイライト部分（キーワード検索の場合）
    """

    document_id: str = Field(..., description="文書ID")
    document_title: str = Field(..., description="文書タイトル")
    content_preview: str = Field(..., description="内容のプレビュー")
    score: float = Field(..., ge=0.0, le=1.0, description="関連性スコア")
    match_type: str = Field(..., description="マッチタイプ")
    confidence_level: str = Field(..., description="信頼度レベル")
    chunk_id: str | None = Field(None, description="チャンクID")
    chunk_index: int | None = Field(None, description="チャンクインデックス")
    highlights: list[str] = Field(default_factory=list, description="ハイライト")

    @classmethod
    def from_domain(cls, item: SearchResultItem) -> "SearchResultItemOutput":
        """ドメインモデルから出力DTOを作成する。

        Args:
            item: SearchResultItemドメインモデル

        Returns:
            出力DTO
        """
        return cls(
            document_id=item.document_id.value,
            document_title=item.document_title,
            content_preview=item.content_preview,
            score=item.score,
            match_type=item.match_type,
            confidence_level=item.confidence_level.value,
            chunk_id=item.chunk_id,
            chunk_index=item.chunk_index,
            highlights=item.highlights or [],
        )


class SearchDocumentsOutput(BaseModel):
    """文書検索の出力DTO。

    Attributes:
        results: 検索結果のリスト
        total_count: 総結果数
        search_time_ms: 検索にかかった時間（ミリ秒）
        query_type: 実行された検索タイプ
        query_text: 元の検索クエリ
        high_confidence_count: 高信頼度の結果数
    """

    results: list[SearchResultItemOutput] = Field(..., description="検索結果")
    total_count: int = Field(..., ge=0, description="総結果数")
    search_time_ms: float = Field(..., ge=0, description="検索時間（ミリ秒）")
    query_type: str = Field(..., description="検索タイプ")
    query_text: str = Field(..., description="検索クエリ")
    high_confidence_count: int = Field(..., ge=0, description="高信頼度結果数")

    @classmethod
    def from_domain(cls, result: SearchResult) -> "SearchDocumentsOutput":
        """ドメインモデルから出力DTOを作成する。

        Args:
            result: SearchResultドメインモデル

        Returns:
            出力DTO
        """
        return cls(
            results=[
                SearchResultItemOutput.from_domain(item) for item in result.results
            ],
            total_count=result.total_count,
            search_time_ms=result.search_time_ms,
            query_type=result.query_type.value,
            query_text=result.query_text,
            high_confidence_count=result.high_confidence_count,
        )


class SearchDocumentsUseCase:
    """文書検索ユースケース。

    キーワード検索、ベクトル検索、ハイブリッド検索を統合して実行する。
    """

    def __init__(
        self,
        document_repository: DocumentRepository,
        vector_search_repository: VectorSearchRepository,
        embedding_service: EmbeddingService,
    ) -> None:
        """ユースケースを初期化する。

        Args:
            document_repository: 文書リポジトリ
            vector_search_repository: ベクトル検索リポジトリ
            embedding_service: 埋め込みサービス
        """
        self._document_repository = document_repository
        self._vector_search_repository = vector_search_repository
        self._embedding_service = embedding_service

    async def execute(self, input_dto: SearchDocumentsInput) -> SearchDocumentsOutput:
        """文書検索を実行する。

        Args:
            input_dto: 入力DTO

        Returns:
            出力DTO

        Raises:
            ValueError: 入力値が不正な場合
            Exception: 検索処理でエラーが発生した場合
        """
        start_time = time.time()
        search_query = input_dto.to_domain()

        try:
            # 検索タイプに応じて処理を分岐
            if search_query.is_keyword_search:
                result = await self._keyword_search(search_query)
            elif search_query.is_vector_search:
                result = await self._vector_search(search_query)
            else:  # hybrid search
                result = await self._hybrid_search(search_query)

            # 検索時間を計算
            search_time_ms = (time.time() - start_time) * 1000

            # SearchResultオブジェクトを作成
            search_result = SearchResult(
                results=result,
                total_count=len(result),
                search_time_ms=search_time_ms,
                query_type=search_query.search_type,
                query_text=search_query.query_text,
            )

            return SearchDocumentsOutput.from_domain(search_result)

        except Exception as e:
            raise Exception(f"Failed to search documents: {e}") from e

    async def _keyword_search(self, query: SearchQuery) -> list[SearchResultItem]:
        """キーワード検索を実行する。

        Args:
            query: 検索クエリ

        Returns:
            検索結果のリスト
        """
        # キーワード検索の実行
        items, total = await self._document_repository.search_by_keyword(
            keyword=query.query_text,
            limit=query.limit,
            offset=query.offset,
        )

        # SearchResultItemに変換
        results = []
        for item in items:
            # 簡易的なスコア計算（実際はより高度なランキングアルゴリズムを使用）
            score = 0.8  # デフォルトスコア

            # 内容プレビューの生成（最初の200文字）
            content_preview = item.title[:200] if len(item.title) > 200 else item.title

            results.append(
                SearchResultItem(
                    document_id=item.id,
                    document_title=item.title,
                    content_preview=content_preview,
                    score=score,
                    match_type="keyword",
                    highlights=[],  # TODO: 実装時にハイライト部分を抽出
                )
            )

        return results

    async def _vector_search(self, query: SearchQuery) -> list[SearchResultItem]:
        """ベクトル検索を実行する。

        Args:
            query: 検索クエリ

        Returns:
            検索結果のリスト
        """
        # クエリの埋め込みベクトルを生成
        embedding_result = await self._embedding_service.generate_embedding(
            query.query_text
        )

        # ベクトル検索の実行
        document_ids = None
        if query.filters and query.filters.get("document_ids"):
            document_ids = [
                DocumentId(value=doc_id) for doc_id in query.filters["document_ids"]
            ]

        search_results = await self._vector_search_repository.search_similar_chunks(
            query_embedding=embedding_result.embedding,
            limit=query.limit,
            similarity_threshold=query.similarity_threshold,
            document_ids=document_ids,
        )

        # SearchResultItemに変換
        results = []
        for vsr in search_results:
            results.append(
                SearchResultItem(
                    document_id=vsr.document_id,
                    document_title=vsr.document_title or "",
                    content_preview=(
                        vsr.content[:200] if len(vsr.content) > 200 else vsr.content
                    ),
                    score=vsr.similarity_score,
                    match_type="vector",
                    chunk_id=vsr.chunk_id,
                    chunk_index=vsr.chunk_index,
                )
            )

        return results

    async def _hybrid_search(self, query: SearchQuery) -> list[SearchResultItem]:
        """ハイブリッド検索を実行する。

        キーワード検索とベクトル検索を組み合わせて結果を統合する。

        Args:
            query: 検索クエリ

        Returns:
            統合された検索結果のリスト
        """
        # 両方の検索を並行実行
        keyword_results = await self._keyword_search(query)
        vector_results = await self._vector_search(query)

        # 結果を統合（文書IDでグループ化）
        result_map: dict[str, SearchResultItem] = {}

        # キーワード検索結果を追加
        for item in keyword_results:
            doc_id = item.document_id.value
            result_map[doc_id] = item

        # ベクトル検索結果を統合
        for item in vector_results:
            doc_id = item.document_id.value
            if doc_id in result_map:
                # 既存の結果と統合（スコアの平均を取る）
                existing = result_map[doc_id]
                combined_score = (existing.score + item.score) / 2
                result_map[doc_id] = SearchResultItem(
                    document_id=existing.document_id,
                    document_title=existing.document_title,
                    content_preview=existing.content_preview,
                    score=combined_score,
                    match_type="both",
                    chunk_id=item.chunk_id,
                    chunk_index=item.chunk_index,
                    highlights=existing.highlights,
                )
            else:
                # ベクトル検索のみの結果
                result_map[doc_id] = item

        # スコアでソートして返す
        results = sorted(result_map.values(), key=lambda x: x.score, reverse=True)[
            : query.limit
        ]

        return results
