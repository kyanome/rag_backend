"""RAGクエリとレスポンスのエンティティ。

RAG（Retrieval-Augmented Generation）のクエリと応答を表すエンティティを定義する。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from ..value_objects import DocumentId, SearchResultItem, UserId


@dataclass
class RAGQuery:
    """RAGクエリを表すエンティティ。

    Attributes:
        id: クエリID
        user_id: ユーザーID（オプション）
        query_text: クエリテキスト
        search_type: 検索タイプ（keyword/vector/hybrid）
        max_results: 検索結果の最大数
        temperature: LLMの生成温度
        include_citations: 引用を含めるかどうか
        metadata: その他のメタデータ
        created_at: 作成日時
    """

    id: UUID = field(default_factory=uuid4)
    query_text: str = ""
    user_id: UserId | None = None
    search_type: str = "hybrid"
    max_results: int = 5
    temperature: float = 0.7
    include_citations: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """初期化後の処理。"""
        if not self.query_text:
            raise ValueError("Query text cannot be empty")
        if self.max_results < 1:
            raise ValueError("Max results must be at least 1")
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")

    @property
    def is_authenticated(self) -> bool:
        """認証済みクエリかどうかを判定する。"""
        return self.user_id is not None


@dataclass
class Citation:
    """引用情報を表すエンティティ。

    Attributes:
        document_id: 文書ID
        document_title: 文書タイトル
        chunk_id: チャンクID
        chunk_index: チャンクインデックス
        content_snippet: 内容の抜粋
        relevance_score: 関連性スコア
        start_position: 引用開始位置（オプション）
        end_position: 引用終了位置（オプション）
        context_before: 前のコンテキスト（オプション）
        context_after: 後のコンテキスト（オプション）
    """

    document_id: DocumentId
    document_title: str
    chunk_id: str | None = None
    chunk_index: int | None = None
    content_snippet: str = ""
    relevance_score: float = 0.0
    start_position: int | None = None
    end_position: int | None = None
    context_before: str | None = None
    context_after: str | None = None

    def __post_init__(self) -> None:
        """初期化後の処理。"""
        if not 0.0 <= self.relevance_score <= 1.0:
            raise ValueError("Relevance score must be between 0.0 and 1.0")

    @classmethod
    def from_search_result(cls, result: SearchResultItem) -> "Citation":
        """検索結果から引用を作成する。

        Args:
            result: 検索結果アイテム

        Returns:
            引用オブジェクト
        """
        return cls(
            document_id=result.document_id,
            document_title=result.document_title,
            chunk_id=result.chunk_id,
            chunk_index=result.chunk_index,
            content_snippet=result.content_preview,
            relevance_score=result.score,
        )


@dataclass
class RAGAnswer:
    """RAG応答を表すエンティティ。

    Attributes:
        id: 応答ID
        query_id: クエリID
        answer_text: 応答テキスト
        citations: 引用情報のリスト
        confidence_score: 信頼度スコア
        search_results_count: 検索結果数
        processing_time_ms: 処理時間（ミリ秒）
        model_name: 使用したモデル名
        token_usage: トークン使用量
        metadata: その他のメタデータ
        created_at: 作成日時
    """

    id: UUID = field(default_factory=uuid4)
    query_id: UUID | None = None
    answer_text: str = ""
    citations: list[Citation] = field(default_factory=list)
    confidence_score: float = 0.0
    search_results_count: int = 0
    processing_time_ms: float = 0.0
    model_name: str = ""
    token_usage: dict[str, int] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """初期化後の処理。"""
        if not self.answer_text:
            raise ValueError("Answer text cannot be empty")
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        if self.processing_time_ms < 0:
            raise ValueError("Processing time cannot be negative")

    @property
    def has_citations(self) -> bool:
        """引用があるかどうかを判定する。"""
        return len(self.citations) > 0

    @property
    def high_confidence(self) -> bool:
        """高信頼度の応答かどうかを判定する。"""
        return self.confidence_score >= 0.8

    def add_citation(self, citation: Citation) -> None:
        """引用を追加する。

        Args:
            citation: 追加する引用
        """
        self.citations.append(citation)

    def calculate_average_relevance(self) -> float:
        """引用の平均関連性スコアを計算する。

        Returns:
            平均関連性スコア（引用がない場合は0.0）
        """
        if not self.citations:
            return 0.0
        total_score = sum(c.relevance_score for c in self.citations)
        return total_score / len(self.citations)
