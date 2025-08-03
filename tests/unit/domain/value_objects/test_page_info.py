"""PageInfo値オブジェクトのテスト。"""

import pytest
from pydantic import ValidationError

from src.domain.value_objects import PageInfo


class TestPageInfo:
    """PageInfoのテストクラス。"""

    def test_create_valid_page_info(self) -> None:
        """正常なPageInfoの作成をテストする。"""
        page_info = PageInfo.create(page=1, page_size=20, total_count=100)

        assert page_info.page == 1
        assert page_info.page_size == 20
        assert page_info.total_count == 100
        assert page_info.total_pages == 5

    def test_create_with_zero_total_count(self) -> None:
        """総件数が0の場合のテスト。"""
        page_info = PageInfo.create(page=1, page_size=20, total_count=0)

        assert page_info.page == 1
        assert page_info.page_size == 20
        assert page_info.total_count == 0
        assert page_info.total_pages == 0

    def test_create_with_partial_last_page(self) -> None:
        """最終ページが部分的な場合のテスト。"""
        page_info = PageInfo.create(page=1, page_size=20, total_count=85)

        assert page_info.total_pages == 5  # 85 / 20 = 4.25 → 5

    def test_invalid_page_number(self) -> None:
        """無効なページ番号のテスト。"""
        with pytest.raises(ValidationError) as exc_info:
            PageInfo(page=0, page_size=20, total_count=100, total_pages=5)

        assert "greater than or equal to 1" in str(exc_info.value)

    def test_invalid_page_size(self) -> None:
        """無効なページサイズのテスト。"""
        # ページサイズが0の場合
        with pytest.raises(ValidationError) as exc_info:
            PageInfo(page=1, page_size=0, total_count=100, total_pages=5)

        assert "greater than or equal to 1" in str(exc_info.value)

        # ページサイズが上限を超える場合
        with pytest.raises(ValidationError) as exc_info:
            PageInfo(page=1, page_size=101, total_count=100, total_pages=1)

        assert "less than or equal to 100" in str(exc_info.value)

    def test_invalid_total_pages(self) -> None:
        """総ページ数の検証エラーのテスト。"""
        with pytest.raises(ValidationError) as exc_info:
            PageInfo(page=1, page_size=20, total_count=100, total_pages=10)

        assert "Total pages must be 5" in str(exc_info.value)

    def test_offset_calculation(self) -> None:
        """オフセット計算のテスト。"""
        # ページ1
        page_info = PageInfo.create(page=1, page_size=20, total_count=100)
        assert page_info.offset == 0

        # ページ2
        page_info = PageInfo.create(page=2, page_size=20, total_count=100)
        assert page_info.offset == 20

        # ページ5
        page_info = PageInfo.create(page=5, page_size=20, total_count=100)
        assert page_info.offset == 80

    def test_has_next_page(self) -> None:
        """次ページの存在判定のテスト。"""
        # 最初のページ
        page_info = PageInfo.create(page=1, page_size=20, total_count=100)
        assert page_info.has_next is True
        assert page_info.next_page == 2

        # 最後のページ
        page_info = PageInfo.create(page=5, page_size=20, total_count=100)
        assert page_info.has_next is False
        assert page_info.next_page is None

        # データが1件もない場合
        page_info = PageInfo.create(page=1, page_size=20, total_count=0)
        assert page_info.has_next is False
        assert page_info.next_page is None

    def test_has_previous_page(self) -> None:
        """前ページの存在判定のテスト。"""
        # 最初のページ
        page_info = PageInfo.create(page=1, page_size=20, total_count=100)
        assert page_info.has_previous is False
        assert page_info.previous_page is None

        # 2ページ目
        page_info = PageInfo.create(page=2, page_size=20, total_count=100)
        assert page_info.has_previous is True
        assert page_info.previous_page == 1

        # 最後のページ
        page_info = PageInfo.create(page=5, page_size=20, total_count=100)
        assert page_info.has_previous is True
        assert page_info.previous_page == 4

    def test_single_page_navigation(self) -> None:
        """1ページのみの場合のナビゲーションテスト。"""
        page_info = PageInfo.create(page=1, page_size=20, total_count=10)

        assert page_info.total_pages == 1
        assert page_info.has_next is False
        assert page_info.has_previous is False
        assert page_info.next_page is None
        assert page_info.previous_page is None

    def test_page_info_is_immutable(self) -> None:
        """PageInfoが不変であることをテストする。"""
        page_info = PageInfo.create(page=1, page_size=20, total_count=100)

        with pytest.raises(ValidationError) as exc_info:
            page_info.page = 2  # type: ignore[misc]

        assert "frozen" in str(exc_info.value)
