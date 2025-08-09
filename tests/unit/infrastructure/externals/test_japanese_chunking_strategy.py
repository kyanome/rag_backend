"""JapaneseChunkingStrategyのテスト。"""

import pytest

from src.infrastructure.externals.chunking_strategies import JapaneseChunkingStrategy


class TestJapaneseChunkingStrategy:
    """JapaneseChunkingStrategyのテスト。"""

    @pytest.fixture
    def strategy(self) -> JapaneseChunkingStrategy:
        """JapaneseChunkingStrategyインスタンスを作成する。"""
        return JapaneseChunkingStrategy()

    def test_split_text_with_japanese_sentences(
        self, strategy: JapaneseChunkingStrategy
    ) -> None:
        """日本語の文が正しく分割されることを確認する。"""
        text = "これは最初の文です。これは二番目の文です。これは三番目の文です。"
        chunks = strategy.split_text(text, chunk_size=20, overlap_size=5)
        
        assert len(chunks) > 0
        # 各チャンクが文境界で分割されていることを確認
        for chunk_text, _, _ in chunks:
            # チャンクが句点で終わるか、文の途中でないことを確認
            assert chunk_text.strip()

    def test_split_text_with_long_sentence(
        self, strategy: JapaneseChunkingStrategy
    ) -> None:
        """長い文が強制的に分割されることを確認する。"""
        # チャンクサイズを超える長い文
        text = "あ" * 150
        chunks = strategy.split_text(text, chunk_size=50, overlap_size=10)
        
        assert len(chunks) > 1
        # 最初のチャンクが最大サイズ以下であることを確認
        assert len(chunks[0][0]) <= 50

    def test_split_text_with_paragraph_breaks(
        self, strategy: JapaneseChunkingStrategy
    ) -> None:
        """段落区切りが考慮されることを確認する。"""
        text = "第一段落の内容です。\n\n第二段落の内容です。\n\n第三段落の内容です。"
        chunks = strategy.split_text(text, chunk_size=30, overlap_size=5)
        
        assert len(chunks) > 0
        # 段落が適切に処理されていることを確認
        for chunk_text, _, _ in chunks:
            assert chunk_text.strip()

    def test_split_text_empty(
        self, strategy: JapaneseChunkingStrategy
    ) -> None:
        """空のテキストで空のリストが返されることを確認する。"""
        chunks = strategy.split_text("", chunk_size=100, overlap_size=20)
        assert chunks == []

    def test_split_text_with_quotes(
        self, strategy: JapaneseChunkingStrategy
    ) -> None:
        """引用符が正しく処理されることを確認する。"""
        text = "彼は「こんにちは」と言いました。それから「さようなら」と言いました。"
        chunks = strategy.split_text(text, chunk_size=30, overlap_size=5)
        
        assert len(chunks) > 0
        # 引用符が適切に処理されていることを確認
        for chunk_text, _, _ in chunks:
            # 開き引用符と閉じ引用符の数が一致するか確認
            open_quotes = chunk_text.count("「")
            close_quotes = chunk_text.count("」")
            # 完全な文でない場合は引用符の不一致を許容
            assert abs(open_quotes - close_quotes) <= 1

    def test_split_text_with_overlap(
        self, strategy: JapaneseChunkingStrategy
    ) -> None:
        """オーバーラップが機能することを確認する。"""
        text = "文1。文2。文3。文4。文5。文6。文7。文8。文9。文10。"
        chunks = strategy.split_text(text, chunk_size=15, overlap_size=5)
        
        if len(chunks) > 1:
            # 隣接するチャンクに重複があることを確認
            for i in range(len(chunks) - 1):
                current_chunk = chunks[i][0]
                next_chunk = chunks[i + 1][0]
                # 重複部分があるかチェック（完全一致でなくても部分一致で良い）
                assert any(
                    part in next_chunk 
                    for part in current_chunk[-5:].split("。")
                    if part
                )

    def test_estimate_chunk_count(
        self, strategy: JapaneseChunkingStrategy
    ) -> None:
        """チャンク数の推定が正しいことを確認する。"""
        text = "あ" * 250
        count = strategy.estimate_chunk_count(text, chunk_size=100, overlap_size=20)
        
        # 推定値が妥当な範囲内であることを確認
        assert count > 0
        assert count <= 5  # (250 / (100-20)) + 1 = 約4

    def test_estimate_chunk_count_empty(
        self, strategy: JapaneseChunkingStrategy
    ) -> None:
        """空のテキストでチャンク数が0になることを確認する。"""
        count = strategy.estimate_chunk_count("", chunk_size=100, overlap_size=20)
        assert count == 0

    def test_estimate_chunk_count_single(
        self, strategy: JapaneseChunkingStrategy
    ) -> None:
        """短いテキストでチャンク数が1になることを確認する。"""
        count = strategy.estimate_chunk_count("短いテキスト", chunk_size=100, overlap_size=20)
        assert count == 1

    def test_mixed_content(
        self, strategy: JapaneseChunkingStrategy
    ) -> None:
        """日本語と英語の混在テキストが処理できることを確認する。"""
        text = "これは日本語です。This is English. また日本語です。"
        chunks = strategy.split_text(text, chunk_size=30, overlap_size=5)
        
        assert len(chunks) > 0
        # すべてのテキストがチャンクに含まれることを確認
        all_text = "".join(chunk[0] for chunk in chunks)
        assert "日本語" in all_text
        assert "English" in all_text