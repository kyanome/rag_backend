"""シンプルなチャンク分割戦略。

言語に依存しない基本的なチャンク分割を行う。
"""

from ....domain.externals import ChunkingStrategy


class SimpleChunkingStrategy(ChunkingStrategy):
    """シンプルなチャンク分割戦略。

    文字数ベースでテキストを均等に分割する基本的な実装。
    英語やその他の言語にも対応。
    """

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
        if not text:
            return []

        chunks = []
        text_length = len(text)

        # 重複を考慮した実効的なステップサイズ
        step_size = chunk_size - overlap_size
        if step_size <= 0:
            step_size = chunk_size  # オーバーラップが大きすぎる場合は無視

        i = 0
        while i < text_length:
            # チャンクの終了位置を計算
            end_pos = min(i + chunk_size, text_length)

            # チャンクテキストを抽出
            chunk_text = text[i:end_pos]

            # 空白のみのチャンクは無視
            if chunk_text.strip():
                chunks.append((chunk_text, i, end_pos))

            # 次の開始位置を計算
            i += step_size

            # 最後のチャンクに到達したら終了
            if i >= text_length:
                break

        return chunks

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
        text_length = len(text)
        if text_length == 0:
            return 0
        if text_length <= chunk_size:
            return 1

        step_size = chunk_size - overlap_size
        if step_size <= 0:
            return 1

        # チャンク数を計算
        return ((text_length - overlap_size) + step_size - 1) // step_size
