"""DocumentListItem値オブジェクトのテスト。"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.domain.value_objects import DocumentId, DocumentListItem


class TestDocumentListItem:
    """DocumentListItemのテストクラス。"""

    def test_create_valid_document_list_item(self) -> None:
        """正常なDocumentListItemの作成をテストする。"""
        document_id = DocumentId.generate()
        created_at = datetime.now()
        updated_at = datetime.now()

        item = DocumentListItem(
            id=document_id,
            title="技術仕様書.pdf",
            file_name="技術仕様書.pdf",
            file_size=1048576,
            content_type="application/pdf",
            category="技術文書",
            tags=["仕様書", "設計"],
            author="山田太郎",
            created_at=created_at,
            updated_at=updated_at,
        )

        assert item.id == document_id
        assert item.title == "技術仕様書.pdf"
        assert item.file_name == "技術仕様書.pdf"
        assert item.file_size == 1048576
        assert item.content_type == "application/pdf"
        assert item.category == "技術文書"
        assert item.tags == ["仕様書", "設計"]
        assert item.author == "山田太郎"
        assert item.created_at == created_at
        assert item.updated_at == updated_at

    def test_create_minimal_document_list_item(self) -> None:
        """最小限の情報でのDocumentListItem作成をテストする。"""
        document_id = DocumentId.generate()
        created_at = datetime.now()

        item = DocumentListItem(
            id=document_id,
            title="test.txt",
            file_name="test.txt",
            file_size=100,
            content_type="text/plain",
            created_at=created_at,
            updated_at=created_at,
        )

        assert item.category is None
        assert item.tags == []
        assert item.author is None

    def test_id_str_property(self) -> None:
        """id_strプロパティのテスト。"""
        document_id = DocumentId.generate()
        item = self._create_test_item(id=document_id)

        assert item.id_str == document_id.value

    def test_file_size_conversions(self) -> None:
        """ファイルサイズ変換のテスト。"""
        # 1MB
        item = self._create_test_item(file_size=1048576)
        assert item.file_size_mb == 1.0
        assert item.file_size_human == "1.0 MB"

        # 500KB
        item = self._create_test_item(file_size=512000)
        assert item.file_size_mb == pytest.approx(0.488, rel=0.01)
        assert item.file_size_human == "500.0 KB"

        # 100B
        item = self._create_test_item(file_size=100)
        assert item.file_size_human == "100 B"

        # 1.5GB
        item = self._create_test_item(file_size=1610612736)
        assert item.file_size_human == "1.5 GB"

    def test_is_recently_updated(self) -> None:
        """更新判定のテスト。"""
        created_at = datetime(2024, 1, 1, 12, 0, 0)

        # 作成日時と更新日時が同じ場合
        item = self._create_test_item(created_at=created_at, updated_at=created_at)
        assert item.is_recently_updated is False

        # 更新されている場合
        updated_at = datetime(2024, 1, 2, 12, 0, 0)
        item = self._create_test_item(created_at=created_at, updated_at=updated_at)
        assert item.is_recently_updated is True

    def test_has_category(self) -> None:
        """カテゴリ存在判定のテスト。"""
        # カテゴリあり
        item = self._create_test_item(category="技術文書")
        assert item.has_category is True

        # カテゴリなし
        item = self._create_test_item(category=None)
        assert item.has_category is False

    def test_has_tags(self) -> None:
        """タグ存在判定のテスト。"""
        # タグあり
        item = self._create_test_item(tags=["Python", "FastAPI"])
        assert item.has_tags is True

        # タグなし（空リスト）
        item = self._create_test_item(tags=[])
        assert item.has_tags is False

    def test_has_author(self) -> None:
        """作成者存在判定のテスト。"""
        # 作成者あり
        item = self._create_test_item(author="山田太郎")
        assert item.has_author is True

        # 作成者なし
        item = self._create_test_item(author=None)
        assert item.has_author is False

    def test_document_list_item_is_immutable(self) -> None:
        """DocumentListItemが不変であることをテストする。"""
        item = self._create_test_item()

        with pytest.raises(ValidationError) as exc_info:
            item.title = "変更"  # type: ignore[misc]

        assert "frozen" in str(exc_info.value)

    def _create_test_item(self, **kwargs) -> DocumentListItem:
        """テスト用のDocumentListItemを作成する。"""
        defaults = {
            "id": DocumentId.generate(),
            "title": "test.pdf",
            "file_name": "test.pdf",
            "file_size": 1048576,
            "content_type": "application/pdf",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        defaults.update(kwargs)
        return DocumentListItem(**defaults)
