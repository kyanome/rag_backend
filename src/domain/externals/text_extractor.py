"""テキスト抽出インターフェース。

外部サービスによるテキスト抽出を抽象化する。
"""

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class ExtractedText(BaseModel):
    """抽出されたテキストを表す値オブジェクト。

    Attributes:
        content: 抽出されたテキスト内容
        metadata: 抽出に関するメタデータ
    """

    content: str = Field(..., description="抽出されたテキスト内容")
    metadata: dict[str, str | int | float] = Field(
        default_factory=dict, description="抽出メタデータ（ページ数、文字数など）"
    )

    model_config = {"frozen": True}

    @property
    def char_count(self) -> int:
        """文字数を返す。"""
        return len(self.content)

    @property
    def is_empty(self) -> bool:
        """テキストが空かどうかを判定する。"""
        return len(self.content.strip()) == 0


class TextExtractor(ABC):
    """テキスト抽出インターフェース。

    文書からテキストを抽出するための抽象インターフェース。
    具体的な実装はインフラストラクチャ層で行う。
    """

    @abstractmethod
    async def extract_text(
        self, content: bytes, content_type: str
    ) -> ExtractedText:
        """文書からテキストを抽出する。

        Args:
            content: 文書のバイナリデータ
            content_type: 文書のMIMEタイプ

        Returns:
            抽出されたテキスト

        Raises:
            ValueError: サポートされていない形式の場合
            Exception: 抽出処理でエラーが発生した場合
        """
        pass

    @abstractmethod
    def supports(self, content_type: str) -> bool:
        """指定されたコンテンツタイプをサポートしているか判定する。

        Args:
            content_type: 文書のMIMEタイプ

        Returns:
            サポートしている場合True
        """
        pass