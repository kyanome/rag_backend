"""DocumentId値オブジェクトのテスト。"""

import uuid

import pytest
from pydantic import ValidationError

from src.domain.value_objects import DocumentId


class TestDocumentId:
    """DocumentIdのテストクラス。"""

    def test_create_with_valid_uuid(self) -> None:
        """有効なUUIDで作成できることを確認する。"""
        valid_uuid = str(uuid.uuid4())
        doc_id = DocumentId(value=valid_uuid)
        assert doc_id.value == valid_uuid

    def test_create_with_invalid_uuid(self) -> None:
        """無効なUUID形式でエラーになることを確認する。"""
        with pytest.raises(ValidationError) as exc_info:
            DocumentId(value="invalid-uuid")

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "Invalid UUID format" in str(errors[0]["msg"])

    def test_create_with_empty_value(self) -> None:
        """空の値でエラーになることを確認する。"""
        with pytest.raises(ValidationError) as exc_info:
            DocumentId(value="")

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "DocumentId value cannot be empty" in str(errors[0]["msg"])

    def test_generate(self) -> None:
        """新しいIDを生成できることを確認する。"""
        doc_id = DocumentId.generate()
        assert doc_id.value
        # 生成されたIDが有効なUUIDであることを確認
        uuid.UUID(doc_id.value)

    def test_str_representation(self) -> None:
        """文字列表現が正しいことを確認する。"""
        valid_uuid = str(uuid.uuid4())
        doc_id = DocumentId(value=valid_uuid)
        assert str(doc_id) == valid_uuid

    def test_equality(self) -> None:
        """等価性の比較が正しく動作することを確認する。"""
        uuid1 = str(uuid.uuid4())
        uuid2 = str(uuid.uuid4())

        doc_id1 = DocumentId(value=uuid1)
        doc_id2 = DocumentId(value=uuid1)
        doc_id3 = DocumentId(value=uuid2)

        assert doc_id1 == doc_id2
        assert doc_id1 != doc_id3
        assert doc_id1 != uuid1  # 文字列との比較はFalse

    def test_hashable(self) -> None:
        """ハッシュ可能であることを確認する。"""
        doc_id1 = DocumentId.generate()
        doc_id2 = DocumentId.generate()

        # setに格納できることを確認
        id_set = {doc_id1, doc_id2}
        assert len(id_set) == 2

        # 同じ値のIDは同じハッシュを持つ
        uuid_str = str(uuid.uuid4())
        doc_id3 = DocumentId(value=uuid_str)
        doc_id4 = DocumentId(value=uuid_str)
        assert hash(doc_id3) == hash(doc_id4)

    def test_immutability(self) -> None:
        """不変性が保たれることを確認する。"""
        doc_id = DocumentId.generate()

        # frozen=Trueなので値の変更はできない
        with pytest.raises(ValidationError):
            doc_id.value = str(uuid.uuid4())
