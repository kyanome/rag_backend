"""文書フィルター値オブジェクト。"""

from datetime import datetime
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator


class DocumentFilter(BaseModel):
    """文書検索用のフィルター条件を表す値オブジェクト。

    Attributes:
        title: タイトル検索キーワード（部分一致）
        created_from: 作成日時の開始
        created_to: 作成日時の終了
        category: カテゴリ
        tags: タグリスト（いずれかに一致）
    """

    title: str | None = Field(None, description="タイトル検索キーワード（部分一致）")
    created_from: datetime | None = Field(None, description="作成日時の開始")
    created_to: datetime | None = Field(None, description="作成日時の終了")
    category: str | None = Field(None, description="カテゴリ")
    tags: list[str] | None = Field(None, description="タグリスト（いずれかに一致）")

    model_config = {"frozen": True}

    @model_validator(mode="after")
    def validate_date_range(self) -> Self:
        """日付範囲の妥当性を検証する。

        Returns:
            検証済みのインスタンス

        Raises:
            ValueError: 日付が不正な場合
        """
        if (
            self.created_to
            and self.created_from
            and self.created_to < self.created_from
        ):
            raise ValueError("created_to must be after or equal to created_from")
        return self

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str | None) -> str | None:
        """タイトルの検証と正規化。

        Args:
            v: タイトル検索キーワード

        Returns:
            正規化されたタイトル
        """
        if v:
            stripped = v.strip()
            return stripped if stripped else None
        return v

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str] | None) -> list[str] | None:
        """タグの検証と正規化。

        Args:
            v: タグリスト

        Returns:
            正規化されたタグリスト
        """
        if v:
            # 空文字列を除外し、重複を排除（順序を維持）
            normalized = []
            seen = set()
            for tag in v:
                stripped = tag.strip()
                if stripped and stripped not in seen:
                    normalized.append(stripped)
                    seen.add(stripped)
            return normalized if normalized else None
        return v

    @property
    def is_empty(self) -> bool:
        """フィルター条件が空かを判定する。

        Returns:
            すべての条件が未設定の場合はTrue
        """
        return all(
            [
                self.title is None,
                self.created_from is None,
                self.created_to is None,
                self.category is None,
                self.tags is None,
            ]
        )

    @property
    def has_date_filter(self) -> bool:
        """日付フィルターが設定されているかを判定する。

        Returns:
            日付フィルターが設定されている場合はTrue
        """
        return self.created_from is not None or self.created_to is not None

    @property
    def has_text_filter(self) -> bool:
        """テキストフィルターが設定されているかを判定する。

        Returns:
            テキストフィルターが設定されている場合はTrue
        """
        return self.title is not None

    @property
    def has_metadata_filter(self) -> bool:
        """メタデータフィルターが設定されているかを判定する。

        Returns:
            メタデータフィルターが設定されている場合はTrue
        """
        return self.category is not None or self.tags is not None
