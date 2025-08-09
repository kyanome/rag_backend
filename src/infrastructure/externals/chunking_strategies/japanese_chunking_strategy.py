"""日本語対応チャンク分割戦略。

日本語テキストの文境界を考慮したチャンク分割を行う。
"""

import re

from janome.tokenizer import Tokenizer

from ....domain.externals import ChunkingStrategy


class JapaneseChunkingStrategy(ChunkingStrategy):
    """日本語対応チャンク分割戦略。

    Janomeを使用して日本語テキストの文境界を適切に認識し、
    意味的なまとまりを保持したチャンク分割を行う。
    """

    def __init__(self) -> None:
        """初期化する。"""
        self.tokenizer = Tokenizer()
        # 日本語の文末記号
        self.sentence_endings = {"。", "！", "？", "．", "…"}
        # 改行も文境界として扱う
        self.paragraph_separator = "\n\n"

    def split_text(
        self, text: str, chunk_size: int, overlap_size: int
    ) -> list[tuple[str, int, int]]:
        """日本語テキストをチャンクに分割する。

        Args:
            text: 分割対象のテキスト
            chunk_size: 最大チャンクサイズ（文字数）
            overlap_size: チャンク間の重複サイズ（文字数）

        Returns:
            チャンクのリスト。各要素は(チャンクテキスト, 開始位置, 終了位置)のタプル
        """
        if not text:
            return []

        # 文を分割
        sentences = self._split_into_sentences(text)
        if not sentences:
            return []

        chunks = []
        current_chunk = []
        current_chunk_size = 0
        current_start = 0

        for sentence_data in sentences:
            sentence, start_pos, end_pos = sentence_data
            sentence_size = len(sentence)

            # 単一の文がチャンクサイズを超える場合
            if sentence_size > chunk_size:
                # 現在のチャンクを保存
                if current_chunk:
                    chunk_text = "".join(current_chunk)
                    chunks.append((chunk_text, current_start, start_pos))
                    current_chunk = []
                    current_chunk_size = 0

                # 長い文を強制的に分割
                for i in range(0, sentence_size, chunk_size - overlap_size):
                    sub_chunk = sentence[i : i + chunk_size]
                    chunk_start = start_pos + i
                    chunk_end = min(start_pos + i + chunk_size, end_pos)
                    chunks.append((sub_chunk, chunk_start, chunk_end))

                current_start = chunk_end
                continue

            # チャンクサイズを超える場合
            if current_chunk_size + sentence_size > chunk_size:
                # 現在のチャンクを保存
                if current_chunk:
                    chunk_text = "".join(current_chunk)
                    chunk_end = start_pos
                    chunks.append((chunk_text, current_start, chunk_end))

                    # オーバーラップ処理
                    if overlap_size > 0 and chunks:
                        # 前のチャンクの末尾から重複部分を取得
                        overlap_sentences = []
                        overlap_size_count = 0
                        for s, _, _ in reversed(
                            sentences[
                                max(
                                    0,
                                    sentences.index(sentence_data)
                                    - len(current_chunk),
                                ) : sentences.index(sentence_data)
                            ]
                        ):
                            if overlap_size_count + len(s) <= overlap_size:
                                overlap_sentences.insert(0, s)
                                overlap_size_count += len(s)
                            else:
                                break
                        current_chunk = overlap_sentences
                        current_chunk_size = overlap_size_count
                    else:
                        current_chunk = []
                        current_chunk_size = 0

                    current_start = start_pos

            # 文を現在のチャンクに追加
            current_chunk.append(sentence)
            current_chunk_size += sentence_size

        # 最後のチャンクを保存
        if current_chunk:
            chunk_text = "".join(current_chunk)
            chunks.append((chunk_text, current_start, len(text)))

        return chunks

    def _split_into_sentences(self, text: str) -> list[tuple[str, int, int]]:
        """テキストを文に分割する。

        Args:
            text: 分割対象のテキスト

        Returns:
            文のリスト。各要素は(文テキスト, 開始位置, 終了位置)のタプル
        """
        sentences = []
        current_sentence = []
        current_start = 0
        i = 0

        while i < len(text):
            char = text[i]
            current_sentence.append(char)

            # 文末記号をチェック
            if char in self.sentence_endings:
                # 次の文字が引用符や括弧の終了でないことを確認
                if i + 1 < len(text) and text[i + 1] not in "」』）】":
                    sentence = "".join(current_sentence)
                    sentences.append((sentence, current_start, i + 1))
                    current_sentence = []
                    current_start = i + 1
            # 段落区切り（連続する改行）をチェック
            elif char == "\n" and i + 1 < len(text) and text[i + 1] == "\n":
                sentence = "".join(current_sentence)
                sentences.append((sentence, current_start, i + 1))
                current_sentence = []
                # 連続する改行をスキップ
                while i + 1 < len(text) and text[i + 1] == "\n":
                    i += 1
                current_start = i + 1

            i += 1

        # 最後の文を追加
        if current_sentence:
            sentence = "".join(current_sentence)
            sentences.append((sentence, current_start, len(text)))

        return sentences

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

        effective_chunk_size = chunk_size - overlap_size
        if effective_chunk_size <= 0:
            return 1

        # 最初のチャンク + 残りのチャンク数
        remaining = text_length - chunk_size
        return 1 + ((remaining + effective_chunk_size - 1) // effective_chunk_size)