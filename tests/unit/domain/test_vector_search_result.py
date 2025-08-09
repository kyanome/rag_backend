"""VectorSearchResult値オブジェクトのテスト。"""

import pytest

from src.domain.value_objects import DocumentId, VectorSearchResult


class TestVectorSearchResult:
    """VectorSearchResult値オブジェクトのテストクラス。"""

    def test_create_valid_result(self):
        """有効な検索結果を作成できることをテスト。"""
        result = VectorSearchResult(
            chunk_id="chunk-001",
            document_id=DocumentId(value="00000000-0000-0000-0000-000000000001"),
            content="This is test content",
            similarity_score=0.95,
            chunk_index=0,
            document_title="Test Document",
        )

        assert result.chunk_id == "chunk-001"
        assert result.document_id.value == "00000000-0000-0000-0000-000000000001"
        assert result.content == "This is test content"
        assert result.similarity_score == 0.95
        assert result.chunk_index == 0
        assert result.document_title == "Test Document"

    def test_confidence_levels(self):
        """信頼度レベルの判定が正しいことをテスト。"""
        # 高信頼度
        high_conf = VectorSearchResult(
            chunk_id="chunk-001",
            document_id=DocumentId(value="00000000-0000-0000-0000-000000000001"),
            content="content",
            similarity_score=0.90,
            chunk_index=0,
        )
        assert high_conf.is_high_confidence
        assert not high_conf.is_medium_confidence
        assert not high_conf.is_low_confidence

        # 中信頼度
        medium_conf = VectorSearchResult(
            chunk_id="chunk-002",
            document_id=DocumentId(value="00000000-0000-0000-0000-000000000002"),
            content="content",
            similarity_score=0.75,
            chunk_index=1,
        )
        assert not medium_conf.is_high_confidence
        assert medium_conf.is_medium_confidence
        assert not medium_conf.is_low_confidence

        # 低信頼度
        low_conf = VectorSearchResult(
            chunk_id="chunk-003",
            document_id=DocumentId(value="00000000-0000-0000-0000-000000000003"),
            content="content",
            similarity_score=0.60,
            chunk_index=2,
        )
        assert not low_conf.is_high_confidence
        assert not low_conf.is_medium_confidence
        assert low_conf.is_low_confidence

    def test_boundary_confidence_levels(self):
        """信頼度レベルの境界値をテスト。"""
        # 0.85 は高信頼度
        boundary_high = VectorSearchResult(
            chunk_id="chunk-001",
            document_id=DocumentId(value="00000000-0000-0000-0000-000000000001"),
            content="content",
            similarity_score=0.85,
            chunk_index=0,
        )
        assert boundary_high.is_high_confidence

        # 0.70 は中信頼度
        boundary_medium = VectorSearchResult(
            chunk_id="chunk-002",
            document_id=DocumentId(value="00000000-0000-0000-0000-000000000002"),
            content="content",
            similarity_score=0.70,
            chunk_index=1,
        )
        assert boundary_medium.is_medium_confidence

    def test_to_dict(self):
        """辞書変換が正しいことをテスト。"""
        result = VectorSearchResult(
            chunk_id="chunk-001",
            document_id=DocumentId(value="00000000-0000-0000-0000-000000000001"),
            content="Test content",
            similarity_score=0.88,
            chunk_index=5,
            document_title="Test Doc",
        )

        result_dict = result.to_dict()

        assert result_dict["chunk_id"] == "chunk-001"
        assert result_dict["document_id"] == "00000000-0000-0000-0000-000000000001"
        assert result_dict["content"] == "Test content"
        assert result_dict["similarity_score"] == 0.88
        assert result_dict["chunk_index"] == 5
        assert result_dict["document_title"] == "Test Doc"
        assert result_dict["confidence_level"] == "high"

    def test_invalid_chunk_id(self):
        """無効なchunk_idで例外が発生することをテスト。"""
        with pytest.raises(ValueError, match="chunk_id cannot be empty"):
            VectorSearchResult(
                chunk_id="",
                document_id=DocumentId(value="00000000-0000-0000-0000-000000000001"),
                content="content",
                similarity_score=0.8,
                chunk_index=0,
            )

    def test_invalid_content(self):
        """無効なcontentで例外が発生することをテスト。"""
        with pytest.raises(ValueError, match="content cannot be empty"):
            VectorSearchResult(
                chunk_id="chunk-001",
                document_id=DocumentId(value="00000000-0000-0000-0000-000000000001"),
                content="",
                similarity_score=0.8,
                chunk_index=0,
            )

    def test_invalid_similarity_score(self):
        """無効な類似度スコアで例外が発生することをテスト。"""
        # スコアが1.0を超える
        with pytest.raises(ValueError, match="similarity_score must be between"):
            VectorSearchResult(
                chunk_id="chunk-001",
                document_id=DocumentId(value="00000000-0000-0000-0000-000000000001"),
                content="content",
                similarity_score=1.5,
                chunk_index=0,
            )

        # スコアが負の値
        with pytest.raises(ValueError, match="similarity_score must be between"):
            VectorSearchResult(
                chunk_id="chunk-001",
                document_id=DocumentId(value="00000000-0000-0000-0000-000000000001"),
                content="content",
                similarity_score=-0.1,
                chunk_index=0,
            )

    def test_invalid_chunk_index(self):
        """無効なchunk_indexで例外が発生することをテスト。"""
        with pytest.raises(ValueError, match="chunk_index must be non-negative"):
            VectorSearchResult(
                chunk_id="chunk-001",
                document_id=DocumentId(value="00000000-0000-0000-0000-000000000001"),
                content="content",
                similarity_score=0.8,
                chunk_index=-1,
            )

    def test_immutability(self):
        """値オブジェクトが不変であることをテスト。"""
        result = VectorSearchResult(
            chunk_id="chunk-001",
            document_id=DocumentId(value="00000000-0000-0000-0000-000000000001"),
            content="content",
            similarity_score=0.8,
            chunk_index=0,
        )

        # frozen=Trueなので属性を変更できない
        with pytest.raises(AttributeError):
            result.chunk_id = "new-id"  # type: ignore

        with pytest.raises(AttributeError):
            result.similarity_score = 0.9  # type: ignore
