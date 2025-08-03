"""DocumentFilter値オブジェクトのテスト。"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.domain.value_objects import DocumentFilter


class TestDocumentFilter:
    """DocumentFilterのテストクラス。"""

    def test_create_empty_filter(self) -> None:
        """空のフィルターの作成をテストする。"""
        filter_ = DocumentFilter()

        assert filter_.title is None
        assert filter_.created_from is None
        assert filter_.created_to is None
        assert filter_.category is None
        assert filter_.tags is None
        assert filter_.is_empty is True

    def test_create_with_title_filter(self) -> None:
        """タイトルフィルターのテスト。"""
        filter_ = DocumentFilter(title="技術")

        assert filter_.title == "技術"
        assert filter_.is_empty is False
        assert filter_.has_text_filter is True
        assert filter_.has_date_filter is False
        assert filter_.has_metadata_filter is False

    def test_title_normalization(self) -> None:
        """タイトルの正規化のテスト。"""
        # 前後の空白が削除される
        filter_ = DocumentFilter(title="  技術文書  ")
        assert filter_.title == "技術文書"

        # 空文字列はNoneになる
        filter_ = DocumentFilter(title="   ")
        assert filter_.title is None

    def test_create_with_date_filter(self) -> None:
        """日付フィルターのテスト。"""
        created_from = datetime(2024, 1, 1)
        created_to = datetime(2024, 12, 31)

        filter_ = DocumentFilter(created_from=created_from, created_to=created_to)

        assert filter_.created_from == created_from
        assert filter_.created_to == created_to
        assert filter_.has_date_filter is True
        assert filter_.has_text_filter is False
        assert filter_.has_metadata_filter is False

    def test_invalid_date_range(self) -> None:
        """無効な日付範囲のテスト。"""
        created_from = datetime(2024, 12, 31)
        created_to = datetime(2024, 1, 1)

        with pytest.raises(ValidationError) as exc_info:
            DocumentFilter(created_from=created_from, created_to=created_to)

        assert "created_to must be after or equal to created_from" in str(
            exc_info.value
        )

    def test_valid_same_date_range(self) -> None:
        """同一日付の範囲のテスト。"""
        same_date = datetime(2024, 6, 1)

        filter_ = DocumentFilter(created_from=same_date, created_to=same_date)

        assert filter_.created_from == same_date
        assert filter_.created_to == same_date

    def test_create_with_category_filter(self) -> None:
        """カテゴリフィルターのテスト。"""
        filter_ = DocumentFilter(category="技術文書")

        assert filter_.category == "技術文書"
        assert filter_.has_metadata_filter is True
        assert filter_.has_text_filter is False
        assert filter_.has_date_filter is False

    def test_create_with_tags_filter(self) -> None:
        """タグフィルターのテスト。"""
        filter_ = DocumentFilter(tags=["Python", "FastAPI"])

        assert filter_.tags == ["Python", "FastAPI"]
        assert filter_.has_metadata_filter is True

    def test_tags_normalization(self) -> None:
        """タグの正規化のテスト。"""
        # 空白の削除と重複の排除
        filter_ = DocumentFilter(tags=["  Python  ", "FastAPI", "python", "Python"])

        assert set(filter_.tags or []) == {"Python", "FastAPI", "python"}

        # 空文字列は除外される
        filter_ = DocumentFilter(tags=["Python", "", "  ", "FastAPI"])

        assert set(filter_.tags or []) == {"Python", "FastAPI"}

        # すべて空文字列の場合はNone
        filter_ = DocumentFilter(tags=["", "  "])

        assert filter_.tags is None

    def test_create_with_all_filters(self) -> None:
        """すべてのフィルターを設定したテスト。"""
        created_from = datetime(2024, 1, 1)
        created_to = datetime(2024, 12, 31)

        filter_ = DocumentFilter(
            title="技術",
            created_from=created_from,
            created_to=created_to,
            category="技術文書",
            tags=["Python", "FastAPI"],
        )

        assert filter_.is_empty is False
        assert filter_.has_text_filter is True
        assert filter_.has_date_filter is True
        assert filter_.has_metadata_filter is True

    def test_partial_date_filter(self) -> None:
        """部分的な日付フィルターのテスト。"""
        # created_fromのみ
        filter_ = DocumentFilter(created_from=datetime(2024, 1, 1))
        assert filter_.has_date_filter is True

        # created_toのみ
        filter_ = DocumentFilter(created_to=datetime(2024, 12, 31))
        assert filter_.has_date_filter is True

    def test_document_filter_is_immutable(self) -> None:
        """DocumentFilterが不変であることをテストする。"""
        filter_ = DocumentFilter(title="技術")

        with pytest.raises(ValidationError) as exc_info:
            filter_.title = "変更"  # type: ignore[misc]

        assert "frozen" in str(exc_info.value)
