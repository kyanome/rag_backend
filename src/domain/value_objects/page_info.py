"""ページ情報値オブジェクト。"""

from typing import Self

from pydantic import BaseModel, Field, model_validator


class PageInfo(BaseModel):
    """ページネーション情報を表す値オブジェクト。

    Attributes:
        page: ページ番号（1から開始）
        page_size: 1ページあたりの件数
        total_count: 総件数
        total_pages: 総ページ数
    """

    page: int = Field(..., ge=1, description="ページ番号（1から開始）")
    page_size: int = Field(..., ge=1, le=100, description="1ページあたりの件数")
    total_count: int = Field(..., ge=0, description="総件数")
    total_pages: int = Field(..., ge=0, description="総ページ数")

    model_config = {"frozen": True}

    @model_validator(mode="after")
    def validate_total_pages(self) -> Self:
        """総ページ数の検証。

        Returns:
            検証済みのインスタンス

        Raises:
            ValueError: 総ページ数が正しくない場合
        """
        expected_pages = (
            -(-self.total_count // self.page_size) if self.page_size > 0 else 0
        )
        if self.total_pages != expected_pages:
            raise ValueError(
                f"Total pages must be {expected_pages} for total_count={self.total_count} and page_size={self.page_size}"
            )
        return self

    @classmethod
    def create(cls, page: int, page_size: int, total_count: int) -> "PageInfo":
        """PageInfoを作成する。

        Args:
            page: ページ番号（1から開始）
            page_size: 1ページあたりの件数
            total_count: 総件数

        Returns:
            新しいPageInfoインスタンス
        """
        total_pages = -(-total_count // page_size)  # 切り上げ
        return cls(
            page=page,
            page_size=page_size,
            total_count=total_count,
            total_pages=total_pages,
        )

    @property
    def offset(self) -> int:
        """データベースクエリ用のオフセット値を返す。

        Returns:
            オフセット値
        """
        return (self.page - 1) * self.page_size

    @property
    def has_next(self) -> bool:
        """次のページが存在するかを判定する。

        Returns:
            次のページが存在する場合はTrue
        """
        return self.page < self.total_pages

    @property
    def has_previous(self) -> bool:
        """前のページが存在するかを判定する。

        Returns:
            前のページが存在する場合はTrue
        """
        return self.page > 1

    @property
    def next_page(self) -> int | None:
        """次のページ番号を返す。

        Returns:
            次のページ番号、存在しない場合はNone
        """
        return self.page + 1 if self.has_next else None

    @property
    def previous_page(self) -> int | None:
        """前のページ番号を返す。

        Returns:
            前のページ番号、存在しない場合はNone
        """
        return self.page - 1 if self.has_previous else None
