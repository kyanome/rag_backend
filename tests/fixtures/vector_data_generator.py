"""ベクトル検索テスト用のデータ生成ツール。

大規模なテストデータを生成するためのユーティリティモジュール。
DDD原則に従い、ドメインのvalue objectsを使用してデータを生成します。
"""

import random
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from faker import Faker

from src.domain.entities import Document
from src.domain.value_objects import (
    ChunkMetadata,
    DocumentChunk,
    DocumentId,
    DocumentMetadata,
)


@dataclass
class TestDataConfig:
    """テストデータ生成の設定。"""

    num_documents: int = 100
    chunks_per_document: int = 10
    embedding_dim: int = 1536
    languages: list[str] | None = None
    seed: int | None = None

    def __post_init__(self) -> None:
        """デフォルト値の設定。"""
        if self.languages is None:
            self.languages = ["ja_JP", "en_US"]


class VectorDataGenerator:
    """ベクトル検索用のテストデータ生成クラス。"""

    def __init__(self, config: TestDataConfig | None = None) -> None:
        """初期化。

        Args:
            config: テストデータ生成の設定
        """
        self.config = config or TestDataConfig()
        if self.config.seed:
            random.seed(self.config.seed)
        self.fakers = {
            lang: Faker(lang, seed=self.config.seed) for lang in self.config.languages
        }

    def generate_document(
        self, index: int, language: str = "ja_JP"
    ) -> tuple[Document, list[DocumentChunk]]:
        """単一の文書とそのチャンクを生成。

        Args:
            index: 文書のインデックス番号
            language: 生成する言語

        Returns:
            文書エンティティとチャンクのリスト
        """
        faker = self.fakers.get(language, self.fakers["ja_JP"])

        # 文書IDの生成
        doc_id = DocumentId(value=str(uuid.uuid4()))

        # 文書メタデータの生成
        categories = ["技術文書", "仕様書", "マニュアル", "レポート", "ガイド"]
        tags = faker.words(nb=random.randint(1, 5))

        # タイトルを別途生成
        title = faker.sentence(nb_words=6)
        
        metadata = DocumentMetadata(
            file_name=f"test_doc_{index}_{faker.file_name(extension='pdf')}",
            file_size=random.randint(1000, 10000000),
            content_type="application/pdf",
            author=faker.name(),
            category=random.choice(categories),
            tags=tags,
            description=faker.text(max_nb_chars=200),
            created_at=faker.date_time(tzinfo=UTC),
            updated_at=datetime.now(UTC),
        )

        # 文書コンテンツの生成
        content = "\n\n".join([faker.text(max_nb_chars=1000) for _ in range(10)])

        # 文書エンティティの作成
        document = Document(
            id=doc_id,
            title=title,
            content=content.encode("utf-8"),
            metadata=metadata,
            chunks=[],
        )

        # チャンクの生成
        chunks = self._generate_chunks(doc_id, content, faker)
        document.chunks = chunks

        return document, chunks

    def _generate_chunks(
        self, doc_id: DocumentId, content: str, faker: Faker
    ) -> list[DocumentChunk]:
        """文書のチャンクを生成。

        Args:
            doc_id: 文書ID
            content: 文書のコンテンツ
            faker: Fakerインスタンス

        Returns:
            チャンクのリスト
        """
        chunks = []
        chunk_size = 500
        overlap = 100
        
        # 先にtotal_chunksを計算
        total_chunks = 0
        for i in range(0, len(content), chunk_size - overlap):
            chunk_content = content[i : i + chunk_size]
            if chunk_content.strip():
                total_chunks += 1

        # コンテンツを分割
        for i in range(0, len(content), chunk_size - overlap):
            chunk_content = content[i : i + chunk_size]
            if not chunk_content.strip():
                continue

            chunk_metadata = ChunkMetadata(
                chunk_index=len(chunks),
                start_position=i,
                end_position=min(i + chunk_size, len(content)),
                total_chunks=total_chunks,
                overlap_with_previous=overlap if i > 0 else 0,
                overlap_with_next=overlap if i + chunk_size < len(content) else 0,
            )

            chunk = DocumentChunk(
                id=str(uuid.uuid4()),
                document_id=doc_id,
                content=chunk_content,
                embedding=self._generate_embedding(),
                metadata=chunk_metadata,
            )
            chunks.append(chunk)

        return chunks

    def _generate_embedding(self) -> list[float]:
        """ダミーの埋め込みベクトルを生成。

        Returns:
            埋め込みベクトル
        """
        # 正規化されたランダムベクトルを生成
        vector = [random.gauss(0, 1) for _ in range(self.config.embedding_dim)]

        # L2正規化
        norm = sum(x**2 for x in vector) ** 0.5
        if norm > 0:
            vector = [x / norm for x in vector]

        return vector

    def generate_dataset(self) -> tuple[list[Document], list[DocumentChunk]]:
        """完全なテストデータセットを生成。

        Returns:
            文書リストと全チャンクのリスト
        """
        documents = []
        all_chunks = []

        for i in range(self.config.num_documents):
            # 言語をランダムに選択
            language = random.choice(self.config.languages)

            # 文書とチャンクを生成
            doc, chunks = self.generate_document(i, language)
            documents.append(doc)
            all_chunks.extend(chunks)

        return documents, all_chunks

    def generate_search_queries(
        self, num_queries: int = 10
    ) -> list[tuple[str, list[float]]]:
        """検索クエリとその埋め込みベクトルを生成。

        Args:
            num_queries: 生成するクエリ数

        Returns:
            (クエリテキスト, 埋め込みベクトル)のリスト
        """
        queries = []

        for _ in range(num_queries):
            # 言語をランダムに選択
            language = random.choice(self.config.languages)
            faker = self.fakers[language]

            # クエリテキストを生成
            query_text = faker.sentence(nb_words=random.randint(3, 10))

            # クエリの埋め込みを生成
            query_embedding = self._generate_embedding()

            queries.append((query_text, query_embedding))

        return queries

    def generate_ground_truth(
        self, queries: list[str], documents: list[Document], top_k: int = 5
    ) -> dict[str, list[str]]:
        """検索精度評価用の正解データを生成。

        Args:
            queries: クエリリスト
            documents: 文書リスト
            top_k: 各クエリの正解文書数

        Returns:
            クエリから関連文書IDへのマッピング
        """
        ground_truth = {}

        for query in queries:
            # ランダムに関連文書を選択（実際のテストでは意味的に関連する文書を選択）
            relevant_docs = random.sample(documents, min(top_k, len(documents)))
            ground_truth[query] = [doc.id.value for doc in relevant_docs]

        return ground_truth


def create_performance_test_data(
    num_documents: int = 1000,
    chunks_per_document: int = 10,
) -> tuple[list[Document], list[DocumentChunk]]:
    """パフォーマンステスト用の大規模データセットを生成。

    Args:
        num_documents: 生成する文書数
        chunks_per_document: 文書あたりのチャンク数

    Returns:
        文書リストと全チャンクのリスト
    """
    config = TestDataConfig(
        num_documents=num_documents,
        chunks_per_document=chunks_per_document,
        seed=42,  # 再現性のために固定シード
    )

    generator = VectorDataGenerator(config)
    return generator.generate_dataset()
