"""文書リストアイテム値オブジェクト。"""

from datetime import datetime

from pydantic import BaseModel, Field

from .document_id import DocumentId


class DocumentListItem(BaseModel):
    """文書リスト表示用の簡略化された文書情報を表す値オブジェクト。

    Attributes:
        id: 文書ID
        title: 文書タイトル
        file_name: ファイル名
        file_size: ファイルサイズ（バイト）
        content_type: コンテンツタイプ
        category: カテゴリ
        tags: タグリスト
        author: 作成者
        created_at: 作成日時
        updated_at: 更新日時
    """

    id: DocumentId = Field(..., description="文書ID")
    title: str = Field(..., description="文書タイトル")
    file_name: str = Field(..., description="ファイル名")
    file_size: int = Field(..., gt=0, description="ファイルサイズ（バイト）")
    content_type: str = Field(..., description="コンテンツタイプ")
    category: str | None = Field(None, description="カテゴリ")
    tags: list[str] = Field(default_factory=list, description="タグリスト")
    author: str | None = Field(None, description="作成者")
    created_at: datetime = Field(..., description="作成日時")
    updated_at: datetime = Field(..., description="更新日時")

    model_config = {"frozen": True}

    @property
    def id_str(self) -> str:
        """文書IDを文字列として返す。

        Returns:
            文書ID文字列
        """
        return self.id.value

    @property
    def file_size_mb(self) -> float:
        """ファイルサイズをMB単位で返す。

        Returns:
            ファイルサイズ（MB）
        """
        return self.file_size / (1024 * 1024)

    @property
    def file_size_human(self) -> str:
        """人間が読みやすい形式でファイルサイズを返す。

        Returns:
            フォーマットされたファイルサイズ
        """
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        elif self.file_size < 1024 * 1024 * 1024:
            return f"{self.file_size / (1024 * 1024):.1f} MB"
        else:
            return f"{self.file_size / (1024 * 1024 * 1024):.1f} GB"

    @property
    def is_recently_updated(self) -> bool:
        """最近更新されたかを判定する（作成日時と更新日時が異なる）。

        Returns:
            更新されている場合はTrue
        """
        return self.created_at != self.updated_at

    @property
    def has_category(self) -> bool:
        """カテゴリが設定されているかを判定する。

        Returns:
            カテゴリが設定されている場合はTrue
        """
        return self.category is not None

    @property
    def has_tags(self) -> bool:
        """タグが設定されているかを判定する。

        Returns:
            タグが1つ以上設定されている場合はTrue
        """
        return len(self.tags) > 0

    @property
    def has_author(self) -> bool:
        """作成者が設定されているかを判定する。

        Returns:
            作成者が設定されている場合はTrue
        """
        return self.author is not None
