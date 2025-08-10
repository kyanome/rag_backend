"""LLMサービス関連の値オブジェクト。

Large Language Model（LLM）サービスで使用する値オブジェクトを定義する。
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class LLMRole(str, Enum):
    """メッセージのロール。"""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class LLMMessage(BaseModel):
    """LLMメッセージを表す値オブジェクト。

    Attributes:
        role: メッセージのロール（system, user, assistant）
        content: メッセージの内容
    """

    role: LLMRole = Field(..., description="メッセージのロール")
    content: str = Field(..., description="メッセージの内容")

    model_config = {"frozen": True}


class LLMUsage(BaseModel):
    """トークン使用量を表す値オブジェクト。

    Attributes:
        prompt_tokens: プロンプトのトークン数
        completion_tokens: 生成されたテキストのトークン数
        total_tokens: 合計トークン数
    """

    prompt_tokens: int = Field(0, ge=0, description="プロンプトのトークン数")
    completion_tokens: int = Field(
        0, ge=0, description="生成されたテキストのトークン数"
    )
    total_tokens: int = Field(0, ge=0, description="合計トークン数")

    model_config = {"frozen": True}

    def calculate_cost(
        self, input_price_per_1k: float, output_price_per_1k: float
    ) -> float:
        """コストを計算する。

        Args:
            input_price_per_1k: 入力1000トークンあたりの価格
            output_price_per_1k: 出力1000トークンあたりの価格

        Returns:
            推定コスト
        """
        input_cost = (self.prompt_tokens / 1000) * input_price_per_1k
        output_cost = (self.completion_tokens / 1000) * output_price_per_1k
        return input_cost + output_cost


class LLMRequest(BaseModel):
    """LLMリクエストを表す値オブジェクト。

    Attributes:
        messages: メッセージのリスト
        model: 使用するモデル名
        temperature: 生成のランダム性（0.0-2.0）
        max_tokens: 最大生成トークン数
        top_p: トークン選択の確率閾値
        frequency_penalty: 頻度ペナルティ
        presence_penalty: 存在ペナルティ
        stop: 停止シーケンス
        stream: ストリーミング応答の有効化
    """

    messages: list[LLMMessage] = Field(..., description="メッセージのリスト")
    model: str | None = Field(None, description="使用するモデル名")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="生成のランダム性")
    max_tokens: int | None = Field(None, gt=0, description="最大生成トークン数")
    top_p: float = Field(1.0, ge=0.0, le=1.0, description="トークン選択の確率閾値")
    frequency_penalty: float = Field(0.0, ge=-2.0, le=2.0, description="頻度ペナルティ")
    presence_penalty: float = Field(0.0, ge=-2.0, le=2.0, description="存在ペナルティ")
    stop: list[str] | None = Field(None, description="停止シーケンス")
    stream: bool = Field(False, description="ストリーミング応答の有効化")

    model_config = {"frozen": True}

    @classmethod
    def from_prompt(
        cls,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> "LLMRequest":
        """プロンプトからリクエストを作成する。

        Args:
            prompt: ユーザープロンプト
            system_prompt: システムプロンプト（オプション）
            **kwargs: その他のパラメータ

        Returns:
            LLMリクエスト
        """
        messages = []
        if system_prompt:
            messages.append(LLMMessage(role=LLMRole.SYSTEM, content=system_prompt))
        messages.append(LLMMessage(role=LLMRole.USER, content=prompt))
        return cls(messages=messages, **kwargs)


class LLMResponse(BaseModel):
    """LLM応答を表す値オブジェクト。

    Attributes:
        content: 生成されたテキスト
        model: 使用されたモデル名
        usage: トークン使用量
        finish_reason: 終了理由
        metadata: その他のメタデータ
    """

    content: str = Field(..., description="生成されたテキスト")
    model: str = Field(..., description="使用されたモデル名")
    usage: LLMUsage = Field(..., description="トークン使用量")
    finish_reason: str | None = Field(None, description="終了理由")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="その他のメタデータ"
    )

    model_config = {"frozen": True}

    @property
    def is_complete(self) -> bool:
        """応答が完全かどうかを判定する。"""
        return self.finish_reason == "stop"

    @property
    def is_truncated(self) -> bool:
        """応答が途中で切れているかどうかを判定する。"""
        return self.finish_reason == "length"


class LLMStreamChunk(BaseModel):
    """ストリーミング応答のチャンクを表す値オブジェクト。

    Attributes:
        delta: 差分テキスト
        model: 使用されたモデル名
        finish_reason: 終了理由（最後のチャンクのみ）
        is_final: 最後のチャンクかどうか
    """

    delta: str = Field("", description="差分テキスト")
    model: str | None = Field(None, description="使用されたモデル名")
    finish_reason: str | None = Field(None, description="終了理由")
    is_final: bool = Field(False, description="最後のチャンクかどうか")

    model_config = {"frozen": True}
