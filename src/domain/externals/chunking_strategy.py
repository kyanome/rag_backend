"""チャンク分割戦略インターフェース。

テキストのチャンク分割戦略を抽象化する。
"""

from abc import ABC, abstractmethod


class ChunkingStrategy(ABC):
    """チャンク分割戦略インターフェース。

    テキストを意味的なまとまりでチャンクに分割するための
    抽象インターフェース。具体的な実装はインフラストラクチャ層で行う。
    """

    @abstractmethod
    def split_text(
        self, text: str, chunk_size: int, overlap_size: int
    ) -> list[tuple[str, int, int]]:
        """テキストをチャンクに分割する。

        Args:
            text: 分割対象のテキスト
            chunk_size: 最大チャンクサイズ（文字数）
            overlap_size: チャンク間の重複サイズ（文字数）

        Returns:
            チャンクのリスト。各要素は(チャンクテキスト, 開始位置, 終了位置)のタプル
        """
        pass

    @abstractmethod
    def estimate_chunk_count(
        self, text: str, chunk_size: int, overlap_size: int
    ) -> int:
        """チャンク数を推定する。

        Args:
            text: 分割対象のテキスト
            chunk_size: 最大チャンクサイズ（文字数）
            overlap_size: チャンク間の重複サイズ（文字数）

        Returns:
            推定チャンク数
        """
        pass