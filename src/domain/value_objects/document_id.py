"""文書ID値オブジェクト。"""

import uuid
from typing import Any

from pydantic import BaseModel, Field, field_validator


class DocumentId(BaseModel):
    """文書の一意識別子を表す値オブジェクト。

    Attributes:
        value: UUID形式の文書ID
    """

    value: str = Field(..., description="UUID形式の文書ID")

    model_config = {"frozen": True}

    @field_validator("value")
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        """UUID形式のバリデーション。"""
        if not v:
            raise ValueError("DocumentId value cannot be empty")

        try:
            uuid.UUID(v)
        except ValueError as e:
            raise ValueError(f"Invalid UUID format: {v}") from e

        return v

    @classmethod
    def generate(cls) -> "DocumentId":
        """新しい文書IDを生成する。

        Returns:
            新しいDocumentIdインスタンス
        """
        return cls(value=str(uuid.uuid4()))

    def __str__(self) -> str:
        """文字列表現を返す。"""
        return self.value

    def __eq__(self, other: Any) -> bool:
        """等価性の比較。"""
        if isinstance(other, DocumentId):
            return self.value == other.value
        return False

    def __hash__(self) -> int:
        """ハッシュ値を返す。"""
        return hash(self.value)
