"""文書メタデータ値オブジェクト。"""

from datetime import datetime

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """文書のメタデータを表す値オブジェクト。

    Attributes:
        file_name: ファイル名
        file_size: ファイルサイズ（バイト）
        content_type: コンテンツタイプ（MIME type）
        category: 文書のカテゴリ
        tags: タグのリスト
        created_at: 作成日時
        updated_at: 更新日時
        author: 作成者
        description: 文書の説明
    """

    file_name: str = Field(..., description="ファイル名")
    file_size: int = Field(..., gt=0, description="ファイルサイズ（バイト）")
    content_type: str = Field(..., description="コンテンツタイプ（MIME type）")
    category: str | None = Field(None, description="文書のカテゴリ")
    tags: list[str] = Field(default_factory=list, description="タグのリスト")
    created_at: datetime = Field(..., description="作成日時")
    updated_at: datetime = Field(..., description="更新日時")
    author: str | None = Field(None, description="作成者")
    description: str | None = Field(None, description="文書の説明")

    model_config = {"frozen": True}

    @classmethod
    def create_new(
        cls,
        file_name: str,
        file_size: int,
        content_type: str,
        category: str | None = None,
        tags: list[str] | None = None,
        author: str | None = None,
        description: str | None = None,
    ) -> "DocumentMetadata":
        """新しい文書メタデータを作成する。

        Args:
            file_name: ファイル名
            file_size: ファイルサイズ（バイト）
            content_type: コンテンツタイプ
            category: 文書のカテゴリ
            tags: タグのリスト
            author: 作成者
            description: 文書の説明

        Returns:
            新しいDocumentMetadataインスタンス
        """
        now = datetime.now()
        return cls(
            file_name=file_name,
            file_size=file_size,
            content_type=content_type,
            category=category,
            tags=tags or [],
            created_at=now,
            updated_at=now,
            author=author,
            description=description,
        )

    def update_timestamp(self) -> "DocumentMetadata":
        """更新日時を現在時刻に更新した新しいインスタンスを返す。

        Returns:
            更新されたDocumentMetadataインスタンス
        """
        return self.model_copy(update={"updated_at": datetime.now()})
