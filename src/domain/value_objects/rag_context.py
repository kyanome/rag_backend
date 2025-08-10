"""RAGコンテキストの値オブジェクト。

検索結果から構築されるRAGコンテキストを表す値オブジェクトを定義する。
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator

from .search_result import SearchResultItem


class RAGContext(BaseModel):
    """RAGコンテキストを表す値オブジェクト。

    検索結果から構築される、LLMに渡すコンテキスト情報。

    Attributes:
        query_text: 元のクエリテキスト
        search_results: 検索結果のリスト
        context_text: 構築されたコンテキストテキスト
        total_chunks: 含まれるチャンクの総数
        unique_documents: ユニークな文書数
        max_relevance_score: 最大関連性スコア
        metadata: その他のメタデータ
    """

    query_text: str = Field(..., min_length=1, description="クエリテキスト")
    search_results: list[SearchResultItem] = Field(
        default_factory=list, description="検索結果のリスト"
    )
    context_text: str = Field("", description="構築されたコンテキストテキスト")
    total_chunks: int = Field(0, ge=0, description="チャンクの総数")
    unique_documents: int = Field(0, ge=0, description="ユニークな文書数")
    max_relevance_score: float = Field(
        0.0, ge=0.0, le=1.0, description="最大関連性スコア"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="その他のメタデータ"
    )

    model_config = {"frozen": True}

    @field_validator("search_results")
    @classmethod
    def validate_search_results(
        cls, v: list[SearchResultItem]
    ) -> list[SearchResultItem]:
        """検索結果のバリデーション。"""
        if len(v) > 100:
            raise ValueError("Too many search results (max 100)")
        return v

    @classmethod
    def from_search_results(
        cls,
        query_text: str,
        search_results: list[SearchResultItem],
        max_context_length: int = 4000,
    ) -> "RAGContext":
        """検索結果からRAGコンテキストを構築する。

        Args:
            query_text: クエリテキスト
            search_results: 検索結果のリスト
            max_context_length: コンテキストの最大文字数

        Returns:
            RAGコンテキスト
        """
        if not search_results:
            return cls(
                query_text=query_text,
                search_results=[],
                context_text="",
                total_chunks=0,
                unique_documents=0,
                max_relevance_score=0.0,
            )

        # ユニークな文書IDを収集
        unique_doc_ids = {result.document_id.value for result in search_results}

        # コンテキストテキストを構築
        context_parts = []
        current_length = 0

        for i, result in enumerate(search_results, 1):
            # チャンク情報を含むヘッダー
            header = f"[Document {i}: {result.document_title}]\n"
            content = result.content_preview

            # 最大長をチェック
            chunk_text = header + content + "\n\n"
            if current_length + len(chunk_text) > max_context_length:
                # 残りのスペースに収まる部分だけ追加
                remaining = max_context_length - current_length
                if remaining > len(header):
                    truncated_content = content[: remaining - len(header) - 4]
                    context_parts.append(header + truncated_content + "...\n\n")
                break

            context_parts.append(chunk_text)
            current_length += len(chunk_text)

        context_text = "".join(context_parts).strip()

        # 最大関連性スコアを計算
        max_score = max((r.score for r in search_results), default=0.0)

        return cls(
            query_text=query_text,
            search_results=search_results,
            context_text=context_text,
            total_chunks=len(search_results),
            unique_documents=len(unique_doc_ids),
            max_relevance_score=max_score,
        )

    def is_sufficient(self, min_chunks: int = 1, min_score: float = 0.5) -> bool:
        """コンテキストが十分かどうかを判定する。

        Args:
            min_chunks: 最小チャンク数
            min_score: 最小関連性スコア

        Returns:
            コンテキストが十分な場合True
        """
        return self.total_chunks >= min_chunks and self.max_relevance_score >= min_score

    def get_document_titles(self) -> list[str]:
        """文書タイトルのリストを取得する。

        Returns:
            重複を除いた文書タイトルのリスト
        """
        seen = set()
        titles = []
        for result in self.search_results:
            if result.document_title not in seen:
                seen.add(result.document_title)
                titles.append(result.document_title)
        return titles

    def get_top_results(self, n: int = 3) -> list[SearchResultItem]:
        """上位n件の検索結果を取得する。

        Args:
            n: 取得する件数

        Returns:
            上位n件の検索結果
        """
        return self.search_results[:n]

    def to_prompt_context(self, include_scores: bool = False) -> str:
        """プロンプト用のコンテキストテキストを生成する。

        Args:
            include_scores: スコアを含めるかどうか

        Returns:
            プロンプト用のコンテキストテキスト
        """
        if not self.search_results:
            return "No relevant context found."

        if include_scores:
            parts = []
            for i, result in enumerate(self.search_results, 1):
                parts.append(
                    f"[{i}] {result.document_title} (Score: {result.score:.2f})\n"
                    f"{result.content_preview}\n"
                )
            return "\n".join(parts)

        return self.context_text
