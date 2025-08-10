"""RAGサービスインターフェース。

RAG（Retrieval-Augmented Generation）サービスの抽象インターフェースを定義する。
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from ..entities.rag_query import RAGAnswer, RAGQuery
from ..value_objects.rag_context import RAGContext


class RAGService(ABC):
    """RAGサービスの抽象インターフェース。

    検索拡張生成（RAG）の処理を抽象化する。
    具体的な実装はインフラストラクチャ層で行う。
    """

    @abstractmethod
    async def process_query(
        self,
        query: RAGQuery,
        context: RAGContext,
    ) -> RAGAnswer:
        """RAGクエリを処理して応答を生成する。

        Args:
            query: RAGクエリ
            context: RAGコンテキスト

        Returns:
            RAG応答

        Raises:
            RAGServiceError: RAG処理でエラーが発生した場合
        """
        pass

    @abstractmethod
    def stream_answer(
        self,
        query: RAGQuery,
        context: RAGContext,
    ) -> AsyncIterator[str]:
        """ストリーミング形式で応答を生成する。

        Args:
            query: RAGクエリ
            context: RAGコンテキスト

        Yields:
            応答テキストのチャンク

        Raises:
            RAGServiceError: RAG処理でエラーが発生した場合
        """
        pass

    @abstractmethod
    def build_prompt(
        self,
        query: RAGQuery,
        context: RAGContext,
    ) -> str:
        """RAGプロンプトを構築する。

        Args:
            query: RAGクエリ
            context: RAGコンテキスト

        Returns:
            構築されたプロンプト
        """
        pass

    @abstractmethod
    def extract_citations(
        self,
        answer_text: str,
        context: RAGContext,
    ) -> list:
        """応答テキストから引用を抽出する。

        Args:
            answer_text: 応答テキスト
            context: RAGコンテキスト

        Returns:
            抽出された引用のリスト
        """
        pass

    @abstractmethod
    def validate_answer(
        self,
        answer: RAGAnswer,
        query: RAGQuery,
    ) -> bool:
        """応答の妥当性を検証する。

        Args:
            answer: RAG応答
            query: 元のクエリ

        Returns:
            応答が妥当な場合True
        """
        pass
