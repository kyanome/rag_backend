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

        意味的に関連するテキストに対して高い類似度を持つベクトルを生成する。

        Args:
            text: テキスト

        Returns:
            埋め込みベクトル
        """
        import math
        
        # テキストから特徴を抽出
        text_lower = text.lower()
        
        # 共通の特徴キーワード（RAGシステム関連）
        feature_keywords = {
            "rag": 1.0,
            "ベクトル": 0.9,
            "vector": 0.9,
            "検索": 0.8,
            "search": 0.8,
            "データベース": 0.7,
            "database": 0.7,
            "システム": 0.6,
            "system": 0.6,
            "言語モデル": 0.8,
            "llm": 0.8,
            "embedding": 0.9,
            "埋め込み": 0.9,
            "実装": 0.5,
            "機能": 0.5,
            "api": 0.6,
        }
        
        # ベースベクトルを作成（テキストのハッシュから）
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()
        
        embedding = []
        for i in range(self._dimensions):
            byte_idx = i % len(hash_bytes)
            # ベース値（小さくしておく）
            base_value = (hash_bytes[byte_idx] / 255.0) * 0.2 - 0.1
            
            # 特徴キーワードに基づいてベクトルを調整
            feature_contribution = 0.0
            for keyword, weight in feature_keywords.items():
                if keyword in text_lower:
                    # キーワードごとに異なる次元パターンを生成
                    keyword_hash = hashlib.md5(keyword.encode()).digest()
                    keyword_pattern = keyword_hash[i % len(keyword_hash)] / 255.0
                    feature_contribution += weight * keyword_pattern * 0.5
            
            # 全体的な正規化のために sin/cos パターンを追加
            angle = (i / self._dimensions) * 2 * math.pi
            pattern_value = math.sin(angle) * 0.1 + math.cos(angle * 2) * 0.05
            
            # 最終的な値を計算
            value = base_value + feature_contribution + pattern_value
            
            # -1から1の範囲にクリップ
            value = max(-1.0, min(1.0, value))
            embedding.append(float(value))
        
        # ベクトルを正規化（単位ベクトルにする）
        norm = math.sqrt(sum(v * v for v in embedding))
        if norm > 0:
            embedding = [v / norm for v in embedding]
        
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
