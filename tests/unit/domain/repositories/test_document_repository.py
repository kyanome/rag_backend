"""DocumentRepositoryインターフェースのテスト。"""

from abc import ABC

import pytest

from src.domain.repositories import DocumentRepository


class TestDocumentRepository:
    """DocumentRepositoryインターフェースのテストクラス。"""

    def test_is_abstract_base_class(self) -> None:
        """抽象基底クラスであることを確認する。"""
        assert issubclass(DocumentRepository, ABC)

        # 直接インスタンス化できないことを確認
        with pytest.raises(TypeError):
            DocumentRepository()  # type: ignore

    def test_has_required_methods(self) -> None:
        """必要なメソッドが定義されていることを確認する。"""
        required_methods = [
            "save",
            "find_by_id",
            "find_all",
            "update",
            "delete",
            "exists",
            "find_by_title",
        ]

        for method_name in required_methods:
            assert hasattr(DocumentRepository, method_name)
            method = getattr(DocumentRepository, method_name)
            # 抽象メソッドであることを確認
            assert hasattr(method, "__isabstractmethod__")
            assert method.__isabstractmethod__
