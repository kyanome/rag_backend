"""文書チャンク化ドメインサービス。

文書のチャンク分割に関するビジネスロジックを提供する。
"""

from ..entities import Document
from ..externals import ChunkingStrategy
from ..value_objects import DocumentChunk


class ChunkingService:
    """文書チャンク化サービス。

    文書のテキストをチャンクに分割し、DocumentChunkオブジェクトを
    生成するドメインサービス。外部依存を持たない純粋なビジネスロジック。
    """

    def create_chunks(
        self,
        document: Document,
        text: str,
        strategy: ChunkingStrategy,
        chunk_size: int = 1000,
        overlap_size: int = 200,
    ) -> list[DocumentChunk]:
        """文書からチャンクを生成する。

        Args:
            document: チャンク化対象の文書
            text: 文書から抽出されたテキスト
            strategy: チャンク分割戦略
            chunk_size: 最大チャンクサイズ（文字数）
            overlap_size: チャンク間の重複サイズ（文字数）

        Returns:
            生成されたDocumentChunkのリスト

        Raises:
            ValueError: パラメータが不正な場合
        """
        self._validate_parameters(chunk_size, overlap_size)

        if not text or not text.strip():
            return []

        # 戦略を使用してテキストを分割
        chunks_data = strategy.split_text(text, chunk_size, overlap_size)

        # DocumentChunkオブジェクトを生成
        chunks = []
        total_chunks = len(chunks_data)

        for index, (chunk_text, start_pos, end_pos) in enumerate(chunks_data):
            # 前後のチャンクとの重複を計算
            overlap_with_previous = 0
            overlap_with_next = 0

            if index > 0:
                prev_end = chunks_data[index - 1][2]
                if start_pos < prev_end:
                    overlap_with_previous = prev_end - start_pos

            if index < total_chunks - 1:
                next_start = chunks_data[index + 1][1]
                if end_pos > next_start:
                    overlap_with_next = end_pos - next_start

            chunk = DocumentChunk.create(
                document_id=document.id,
                content=chunk_text,
                chunk_index=index,
                start_position=start_pos,
                end_position=end_pos,
                total_chunks=total_chunks,
                overlap_with_previous=overlap_with_previous,
                overlap_with_next=overlap_with_next,
            )
            chunks.append(chunk)

        return chunks

    def update_document_chunks(
        self, document: Document, chunks: list[DocumentChunk]
    ) -> None:
        """文書のチャンクを更新する。

        Args:
            document: 更新対象の文書
            chunks: 新しいチャンクリスト
        """
        # 既存のチャンクをクリア
        document.clear_chunks()

        # 新しいチャンクを追加
        for chunk in chunks:
            document.add_chunk(chunk)

    def _validate_parameters(self, chunk_size: int, overlap_size: int) -> None:
        """パラメータを検証する。

        Args:
            chunk_size: チャンクサイズ
            overlap_size: 重複サイズ

        Raises:
            ValueError: パラメータが不正な場合
        """
        if chunk_size <= 0:
            raise ValueError("Chunk size must be positive")

        if overlap_size < 0:
            raise ValueError("Overlap size must be non-negative")

        if overlap_size >= chunk_size:
            raise ValueError("Overlap size must be less than chunk size")

    def calculate_chunking_metrics(
        self, text: str, chunk_size: int, overlap_size: int
    ) -> dict[str, int]:
        """チャンク化のメトリクスを計算する。

        Args:
            text: 対象テキスト
            chunk_size: チャンクサイズ
            overlap_size: 重複サイズ

        Returns:
            メトリクス情報（文字数、推定チャンク数など）
        """
        text_length = len(text)
        effective_chunk_size = chunk_size - overlap_size

        if text_length <= chunk_size:
            estimated_chunks = 1 if text_length > 0 else 0
        else:
            # 最初のチャンク + 残りのチャンク数
            remaining_text = text_length - chunk_size
            estimated_chunks = 1 + (
                (remaining_text + effective_chunk_size - 1) // effective_chunk_size
            )

        return {
            "text_length": text_length,
            "chunk_size": chunk_size,
            "overlap_size": overlap_size,
            "estimated_chunks": estimated_chunks,
        }