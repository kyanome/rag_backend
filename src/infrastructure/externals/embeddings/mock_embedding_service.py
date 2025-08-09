"""テスト用のモック埋め込みベクトル生成サービス。"""

import hashlib

from ....domain.exceptions import InvalidTextError
from ....domain.externals import EmbeddingResult, EmbeddingService


class MockEmbeddingService(EmbeddingService):
    """テスト用のモック埋め込みベクトル生成サービス。

    実際のAPIを呼び出さずに、決定論的な埋め込みベクトルを生成する。
    """

    def __init__(self, model: str = "mock-model", dimensions: int = 1536):
        """初期化する。

        Args:
            model: モデル名
            dimensions: 埋め込みベクトルの次元数
        """
        self._model = model
        self._dimensions = dimensions

    def _generate_deterministic_embedding(self, text: str) -> list[float]:
        """テキストから決定論的な埋め込みベクトルを生成する。

        Args:
            text: テキスト

        Returns:
            埋め込みベクトル
        """
        # テキストのハッシュ値を基に決定論的なベクトルを生成
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()

        # ハッシュ値を使って次元数分の浮動小数点数を生成
        embedding = []
        for i in range(self._dimensions):
            # バイト値を-1から1の範囲に正規化
            byte_idx = i % len(hash_bytes)
            value = (hash_bytes[byte_idx] / 255.0) * 2 - 1
            # 少し変動を加える
            value += (i / self._dimensions) * 0.1
            embedding.append(float(value))

        return embedding

    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """単一のテキストから埋め込みベクトルを生成する。

        Args:
            text: 埋め込みを生成するテキスト

        Returns:
            埋め込みベクトル生成結果

        Raises:
            InvalidTextError: テキストが空または無効な場合
        """
        if not text or not text.strip():
            raise InvalidTextError("Text cannot be empty")

        embedding = self._generate_deterministic_embedding(text)

        return EmbeddingResult(
            embedding=embedding,
            model=self._model,
            dimensions=self._dimensions,
        )

    async def generate_batch_embeddings(
        self, texts: list[str]
    ) -> list[EmbeddingResult]:
        """複数のテキストから埋め込みベクトルをバッチ生成する。

        Args:
            texts: 埋め込みを生成するテキストのリスト

        Returns:
            埋め込みベクトル生成結果のリスト

        Raises:
            InvalidTextError: テキストリストが空または無効な場合
        """
        if not texts:
            raise InvalidTextError("Text list cannot be empty")

        # 空のテキストをフィルタリング
        valid_texts = [text for text in texts if text and text.strip()]
        if not valid_texts:
            raise InvalidTextError("All texts are empty")

        results: list[EmbeddingResult] = []
        for text in valid_texts:
            embedding = self._generate_deterministic_embedding(text)
            results.append(
                EmbeddingResult(
                    embedding=embedding,
                    model=self._model,
                    dimensions=self._dimensions,
                )
            )

        return results

    def get_model_name(self) -> str:
        """使用しているモデル名を取得する。

        Returns:
            モデル名
        """
        return self._model

    def get_dimensions(self) -> int:
        """埋め込みベクトルの次元数を取得する。

        Returns:
            次元数
        """
        return self._dimensions
