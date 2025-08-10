"""Mock LLMサービスのテスト。"""

import pytest

from src.domain.exceptions import LLMInvalidRequestError, LLMRateLimitError
from src.domain.value_objects.llm_types import LLMRequest
from src.infrastructure.externals.llms import MockLLMService


@pytest.fixture
def mock_llm_service() -> MockLLMService:
    """Mock LLMサービスのフィクスチャ。"""
    return MockLLMService(
        model="test-model",
        default_response="Test response",
        stream_delay=0.001,
    )


class TestMockLLMService:
    """Mock LLMサービスのテストクラス。"""

    async def test_generate_response(self, mock_llm_service: MockLLMService) -> None:
        """基本的な応答生成のテスト。"""
        request = LLMRequest.from_prompt(
            prompt="Hello, how are you?",
            temperature=0.5,
        )

        response = await mock_llm_service.generate_response(request)

        assert response.content
        assert response.model == "test-model"
        assert response.usage.total_tokens > 0
        assert response.finish_reason == "stop"
        assert response.is_complete

    async def test_generate_response_with_system_prompt(
        self, mock_llm_service: MockLLMService
    ) -> None:
        """システムプロンプト付き応答生成のテスト。"""
        request = LLMRequest.from_prompt(
            prompt="What is Python?",
            system_prompt="You are a helpful assistant.",
            temperature=0.7,
        )

        response = await mock_llm_service.generate_response(request)

        assert response.content
        assert "interesting question" in response.content

    async def test_stream_response(self, mock_llm_service: MockLLMService) -> None:
        """ストリーミング応答のテスト。"""
        request = LLMRequest.from_prompt(
            prompt="Tell me a story",
            stream=True,
        )

        chunks = []
        async for chunk in mock_llm_service.stream_response(request):
            chunks.append(chunk)
            assert chunk.delta or chunk.is_final
            if chunk.is_final:
                assert chunk.finish_reason == "stop"

        assert len(chunks) > 1
        full_text = "".join(c.delta for c in chunks)
        assert full_text

    async def test_rate_limit_simulation(
        self, mock_llm_service: MockLLMService
    ) -> None:
        """レート制限シミュレーションのテスト。"""
        mock_llm_service.enable_rate_limit_simulation(True)

        request = LLMRequest.from_prompt("Test")

        # 3回目の呼び出しでレート制限エラー
        await mock_llm_service.generate_response(request)
        await mock_llm_service.generate_response(request)

        with pytest.raises(LLMRateLimitError) as exc_info:
            await mock_llm_service.generate_response(request)

        assert exc_info.value.retry_after == 5

    async def test_error_simulation(self, mock_llm_service: MockLLMService) -> None:
        """エラーシミュレーションのテスト。"""
        mock_llm_service.enable_error_simulation(True)

        request = LLMRequest.from_prompt("Test")

        with pytest.raises(LLMInvalidRequestError) as exc_info:
            await mock_llm_service.generate_response(request)

        assert "Mock error" in str(exc_info.value)

    async def test_custom_response(self, mock_llm_service: MockLLMService) -> None:
        """カスタム応答設定のテスト。"""
        custom_response = "This is a custom response"
        mock_llm_service.set_response(custom_response)

        request = LLMRequest.from_prompt("Any question")
        response = await mock_llm_service.generate_response(request)

        assert response.content == custom_response

    def test_model_info(self, mock_llm_service: MockLLMService) -> None:
        """モデル情報取得のテスト。"""
        info = mock_llm_service.get_model_info()

        assert info["name"] == "test-model"
        assert info["type"] == "mock"
        assert info["max_tokens"] == 4096
        assert info["supports_streaming"] is True

    def test_supports_streaming(self, mock_llm_service: MockLLMService) -> None:
        """ストリーミングサポートのテスト。"""
        assert mock_llm_service.supports_streaming() is True

    def test_get_max_tokens(self, mock_llm_service: MockLLMService) -> None:
        """最大トークン数取得のテスト。"""
        assert mock_llm_service.get_max_tokens() == 4096
