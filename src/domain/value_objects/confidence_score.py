"""信頼度スコアの値オブジェクト。

RAG応答の信頼度を表す値オブジェクトを定義する。
"""

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class ConfidenceLevel(str, Enum):
    """信頼度レベル。"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"


class ConfidenceScore(BaseModel):
    """信頼度スコアを表す値オブジェクト。

    RAG応答の信頼度を数値とレベルで表現する。

    Attributes:
        score: 信頼度スコア（0.0-1.0）
        level: 信頼度レベル
        factors: スコアに影響した要因
        explanation: 信頼度の説明
    """

    score: float = Field(..., ge=0.0, le=1.0, description="信頼度スコア")
    level: ConfidenceLevel = Field(..., description="信頼度レベル")
    factors: dict[str, float] = Field(
        default_factory=dict, description="スコアに影響した要因"
    )
    explanation: str = Field("", description="信頼度の説明")

    model_config = {"frozen": True}

    @field_validator("factors")
    @classmethod
    def validate_factors(cls, v: dict[str, float]) -> dict[str, float]:
        """要因のバリデーション。"""
        for key, value in v.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"Factor '{key}' must be between 0.0 and 1.0")
        return v

    @classmethod
    def calculate(
        cls,
        search_relevance: float,
        context_coverage: float,
        answer_coherence: float = 1.0,
        source_reliability: float = 1.0,
    ) -> "ConfidenceScore":
        """各要因から信頼度スコアを計算する。

        Args:
            search_relevance: 検索結果の関連性（0.0-1.0）
            context_coverage: コンテキストのカバレッジ（0.0-1.0）
            answer_coherence: 回答の一貫性（0.0-1.0）
            source_reliability: ソースの信頼性（0.0-1.0）

        Returns:
            計算された信頼度スコア
        """
        # 重み付き平均を計算
        weights = {
            "search_relevance": 0.35,
            "context_coverage": 0.30,
            "answer_coherence": 0.20,
            "source_reliability": 0.15,
        }

        factors = {
            "search_relevance": search_relevance,
            "context_coverage": context_coverage,
            "answer_coherence": answer_coherence,
            "source_reliability": source_reliability,
        }

        weighted_sum = sum(factors[key] * weights[key] for key in weights)

        # スコアからレベルを決定
        if weighted_sum >= 0.85:
            level = ConfidenceLevel.HIGH
            explanation = "High confidence based on relevant search results and comprehensive context"
        elif weighted_sum >= 0.65:
            level = ConfidenceLevel.MEDIUM
            explanation = "Medium confidence with adequate search results and context"
        elif weighted_sum >= 0.45:
            level = ConfidenceLevel.LOW
            explanation = "Low confidence due to limited relevant information"
        else:
            level = ConfidenceLevel.VERY_LOW
            explanation = "Very low confidence - insufficient information to provide reliable answer"

        return cls(
            score=round(weighted_sum, 3),
            level=level,
            factors=factors,
            explanation=explanation,
        )

    @classmethod
    def from_context_and_results(
        cls,
        max_search_score: float,
        num_results: int,
        num_documents: int,
        has_direct_match: bool = False,
    ) -> "ConfidenceScore":
        """コンテキストと検索結果から信頼度スコアを計算する。

        Args:
            max_search_score: 最大検索スコア
            num_results: 検索結果数
            num_documents: ユニークな文書数
            has_direct_match: 直接的な一致があるか

        Returns:
            計算された信頼度スコア
        """
        # 検索関連性を計算
        search_relevance = max_search_score
        if has_direct_match:
            search_relevance = min(1.0, search_relevance * 1.2)

        # コンテキストカバレッジを計算
        context_coverage = min(1.0, num_results / 5.0)  # 5件以上で最大
        if num_documents > 1:
            context_coverage = min(1.0, context_coverage * 1.1)  # 複数文書でボーナス

        return cls.calculate(
            search_relevance=search_relevance,
            context_coverage=context_coverage,
        )

    @property
    def is_high_confidence(self) -> bool:
        """高信頼度かどうかを判定する。"""
        return self.level == ConfidenceLevel.HIGH

    @property
    def is_acceptable(self) -> bool:
        """許容可能な信頼度かどうかを判定する。"""
        return self.level in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM)

    def to_dict(self) -> dict:
        """辞書形式に変換する。"""
        return {
            "score": self.score,
            "level": self.level.value,
            "factors": self.factors,
            "explanation": self.explanation,
        }
