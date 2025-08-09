"""モック埋め込みサービスの単体テスト。"""

import pytest

from src.domain.exceptions import InvalidTextError
from src.infrastructure.externals.embeddings import MockEmbeddingService


class TestMockEmbeddingService:
    """MockEmbeddingServiceのテスト。"""

    @pytest.fixture
    def service(self) -> MockEmbeddingService:
        """テスト用のサービスインスタンスを作成する。"""
        return MockEmbeddingService(model="test-model", dimensions=384)

    @pytest.mark.asyncio
    async def test_generate_embedding_success(
        self, service: MockEmbeddingService
    ) -> None:
        """正常に埋め込みベクトルを生成できることを確認する。"""
        # 実行
        result = await service.generate_embedding("This is a test text")

        # 検証
        assert result.model == "test-model"
        assert result.dimensions == 384
        assert len(result.embedding) == 384
        assert all(isinstance(x, float) for x in result.embedding)
        assert all(-1.1 <= x <= 1.1 for x in result.embedding)
        assert result.is_valid

    @pytest.mark.asyncio
    async def test_generate_embedding_deterministic(
        self, service: MockEmbeddingService
    ) -> None:
        """同じテキストから同じ埋め込みベクトルが生成されることを確認する。"""
        text = "Deterministic test"

        # 実行
        result1 = await service.generate_embedding(text)
        result2 = await service.generate_embedding(text)

        # 検証
        assert result1.embedding == result2.embedding

    @pytest.mark.asyncio
    async def test_generate_embedding_different_texts(
        self, service: MockEmbeddingService
    ) -> None:
        """異なるテキストから異なる埋め込みベクトルが生成されることを確認する。"""
        # 実行
        result1 = await service.generate_embedding("Text 1")
        result2 = await service.generate_embedding("Text 2")

        # 検証
        assert result1.embedding != result2.embedding

    @pytest.mark.asyncio
    async def test_generate_embedding_empty_text(
        self, service: MockEmbeddingService
    ) -> None:
        """空のテキストでエラーが発生することを確認する。"""
        # 実行と検証
        with pytest.raises(InvalidTextError, match="Text cannot be empty"):
            await service.generate_embedding("")

        with pytest.raises(InvalidTextError, match="Text cannot be empty"):
            await service.generate_embedding("   ")

    @pytest.mark.asyncio
    async def test_generate_batch_embeddings_success(
        self, service: MockEmbeddingService
    ) -> None:
        """バッチで埋め込みベクトルを生成できることを確認する。"""
        texts = ["Text 1", "Text 2", "Text 3"]

        # 実行
        results = await service.generate_batch_embeddings(texts)

        # 検証
        assert len(results) == 3
        for _i, result in enumerate(results):
            assert result.model == "test-model"
            assert result.dimensions == 384
            assert len(result.embedding) == 384
            assert result.is_valid

        # 各テキストで異なる埋め込みが生成される
        assert results[0].embedding != results[1].embedding
        assert results[1].embedding != results[2].embedding

    @pytest.mark.asyncio
    async def test_generate_batch_embeddings_with_empty_texts(
        self, service: MockEmbeddingService
    ) -> None:
        """空のテキストを含むバッチでも処理できることを確認する。"""
        texts = ["Text 1", "", "Text 3", "   "]

        # 実行
        results = await service.generate_batch_embeddings(texts)

        # 検証（空のテキストはフィルタリングされる）
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_generate_batch_embeddings_empty_list(
        self, service: MockEmbeddingService
    ) -> None:
        """空のリストでエラーが発生することを確認する。"""
        # 実行と検証
        with pytest.raises(InvalidTextError, match="Text list cannot be empty"):
            await service.generate_batch_embeddings([])

    @pytest.mark.asyncio
    async def test_generate_batch_embeddings_all_empty(
        self, service: MockEmbeddingService
    ) -> None:
        """全て空のテキストのリストでエラーが発生することを確認する。"""
        # 実行と検証
        with pytest.raises(InvalidTextError, match="All texts are empty"):
            await service.generate_batch_embeddings(["", "   ", "\n", "\t"])

    def test_get_model_name(self, service: MockEmbeddingService) -> None:
        """モデル名を取得できることを確認する。"""
        assert service.get_model_name() == "test-model"

    def test_get_dimensions(self, service: MockEmbeddingService) -> None:
        """次元数を取得できることを確認する。"""
        assert service.get_dimensions() == 384

    def test_default_dimensions(self) -> None:
        """デフォルトの次元数が1536であることを確認する。"""
        service = MockEmbeddingService()
        assert service.get_dimensions() == 1536
