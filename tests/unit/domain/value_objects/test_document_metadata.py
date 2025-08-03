"""DocumentMetadata値オブジェクトのテスト。"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.domain.value_objects import DocumentMetadata


class TestDocumentMetadata:
    """DocumentMetadataのテストクラス。"""

    def test_create_with_required_fields(self) -> None:
        """必須フィールドのみで作成できることを確認する。"""
        now = datetime.now()
        metadata = DocumentMetadata(
            file_name="test.pdf",
            file_size=1024,
            content_type="application/pdf",
            created_at=now,
            updated_at=now,
        )

        assert metadata.file_name == "test.pdf"
        assert metadata.file_size == 1024
        assert metadata.content_type == "application/pdf"
        assert metadata.created_at == now
        assert metadata.updated_at == now
        assert metadata.category is None
        assert metadata.tags == []
        assert metadata.author is None
        assert metadata.description is None

    def test_create_with_all_fields(self) -> None:
        """すべてのフィールドで作成できることを確認する。"""
        now = datetime.now()
        metadata = DocumentMetadata(
            file_name="report.docx",
            file_size=2048,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            category="報告書",
            tags=["月次", "売上"],
            created_at=now,
            updated_at=now,
            author="田中太郎",
            description="2024年1月の月次売上報告書",
        )

        assert metadata.file_name == "report.docx"
        assert metadata.file_size == 2048
        assert metadata.category == "報告書"
        assert metadata.tags == ["月次", "売上"]
        assert metadata.author == "田中太郎"
        assert metadata.description == "2024年1月の月次売上報告書"

    def test_create_new_helper(self) -> None:
        """create_newヘルパーメソッドが正しく動作することを確認する。"""
        before = datetime.now()
        metadata = DocumentMetadata.create_new(
            file_name="test.txt",
            file_size=512,
            content_type="text/plain",
            category="テスト",
            tags=["サンプル"],
            author="テストユーザー",
            description="テスト用ファイル",
        )
        after = datetime.now()

        assert metadata.file_name == "test.txt"
        assert metadata.file_size == 512
        assert metadata.content_type == "text/plain"
        assert metadata.category == "テスト"
        assert metadata.tags == ["サンプル"]
        assert metadata.author == "テストユーザー"
        assert metadata.description == "テスト用ファイル"
        assert before <= metadata.created_at <= after
        assert metadata.created_at == metadata.updated_at

    def test_invalid_file_size(self) -> None:
        """無効なファイルサイズでエラーになることを確認する。"""
        now = datetime.now()

        with pytest.raises(ValidationError):
            DocumentMetadata(
                file_name="test.pdf",
                file_size=0,  # 0以下は無効
                content_type="application/pdf",
                created_at=now,
                updated_at=now,
            )

        with pytest.raises(ValidationError):
            DocumentMetadata(
                file_name="test.pdf",
                file_size=-1,  # 負の値は無効
                content_type="application/pdf",
                created_at=now,
                updated_at=now,
            )

    def test_update_timestamp(self) -> None:
        """タイムスタンプ更新が正しく動作することを確認する。"""
        original_time = datetime(2024, 1, 1, 12, 0, 0)
        metadata = DocumentMetadata(
            file_name="test.pdf",
            file_size=1024,
            content_type="application/pdf",
            created_at=original_time,
            updated_at=original_time,
        )

        before_update = datetime.now()
        updated_metadata = metadata.update_timestamp()
        after_update = datetime.now()

        # 元のインスタンスは変更されない
        assert metadata.updated_at == original_time

        # 新しいインスタンスは更新されている
        assert updated_metadata.created_at == original_time  # created_atは変わらない
        assert before_update <= updated_metadata.updated_at <= after_update
        assert updated_metadata.file_name == metadata.file_name
        assert updated_metadata.file_size == metadata.file_size

    def test_immutability(self) -> None:
        """不変性が保たれることを確認する。"""
        metadata = DocumentMetadata.create_new(
            file_name="test.pdf",
            file_size=1024,
            content_type="application/pdf",
        )

        with pytest.raises(ValidationError):
            metadata.file_name = "changed.pdf"

        # Pydantic v2のfrozenはリスト内容の変更を防げない
        # 代わりにmodel_copyで新しいインスタンスを作成
        original_tags = metadata.tags.copy()
        new_metadata = metadata.model_copy(update={"tags": metadata.tags + ["new-tag"]})
        assert metadata.tags == original_tags
        assert new_metadata.tags == original_tags + ["new-tag"]
