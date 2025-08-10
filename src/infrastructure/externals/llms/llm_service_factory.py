"""LLMサービスファクトリー。

設定に基づいて適切なLLMサービス実装を返すファクトリー。
"""

from typing import Any, Literal

from ....domain.externals import LLMService
from .mock_llm_service import MockLLMService
from .ollama_llm_service import OllamaLLMService
from .openai_llm_service import OpenAILLMService

LLMProvider = Literal["openai", "ollama", "mock"]


class LLMServiceFactory:
    """LLMサービスファクトリー。

    設定に応じて適切なLLMサービスの実装を返す。
    """

    @staticmethod
    def create(
        provider: LLMProvider,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        organization: str | None = None,
        timeout: float = 60.0,
        **kwargs: Any,
    ) -> LLMService:
        """LLMサービスを作成する。

        Args:
            provider: プロバイダー名（openai, ollama, mock）
            api_key: APIキー（OpenAIの場合必須）
            model: モデル名（省略時はデフォルト値を使用）
            base_url: ベースURL（Ollamaの場合のみ）
            organization: 組織ID（OpenAIの場合のみ）
            timeout: タイムアウト秒数
            **kwargs: その他のプロバイダー固有パラメータ

        Returns:
            LLMサービスの実装

        Raises:
            ValueError: 不正なプロバイダー名または必須パラメータが不足している場合
        """
        if provider == "openai":
            if not api_key:
                raise ValueError("OpenAI provider requires api_key")
            return OpenAILLMService(
                api_key=api_key,
                model=model or "gpt-3.5-turbo",
                organization=organization,
                timeout=timeout,
                max_retries=kwargs.get("max_retries", 3),
            )

        elif provider == "ollama":
            return OllamaLLMService(
                base_url=base_url or "http://localhost:11434",
                model=model or "llama2",
                timeout=timeout,
            )

        elif provider == "mock":
            return MockLLMService(
                model=model or "mock-model",
                default_response=kwargs.get(
                    "default_response", "This is a mock response."
                ),
                stream_delay=kwargs.get("stream_delay", 0.01),
                simulate_rate_limit=kwargs.get("simulate_rate_limit", False),
                simulate_error=kwargs.get("simulate_error", False),
            )

        else:
            raise ValueError(
                f"Unknown LLM provider: {provider}. "
                "Supported providers: openai, ollama, mock"
            )

    @staticmethod
    def from_settings(settings: Any) -> LLMService:
        """設定オブジェクトからLLMサービスを作成する。

        Args:
            settings: 設定オブジェクト（Settings インスタンス）

        Returns:
            LLMサービスの実装

        Raises:
            ValueError: 設定が不正な場合
        """
        provider = getattr(settings, "llm_provider", "mock")

        if provider == "openai":
            return LLMServiceFactory.create(
                provider="openai",
                api_key=settings.openai_api_key,
                model=settings.openai_llm_model,
                timeout=getattr(settings, "llm_timeout", 60.0),
            )

        elif provider == "ollama":
            return LLMServiceFactory.create(
                provider="ollama",
                base_url=settings.ollama_base_url,
                model=settings.ollama_llm_model,
                timeout=getattr(settings, "llm_timeout", 120.0),
            )

        else:  # default to mock
            return LLMServiceFactory.create(
                provider="mock",
                model="mock-model",
            )
