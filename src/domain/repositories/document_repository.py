"""文書リポジトリのインターフェース定義。"""

from abc import ABC, abstractmethod

from ..entities import Document
from ..value_objects import DocumentFilter, DocumentId, DocumentListItem


class DocumentRepository(ABC):
    """文書リポジトリの抽象基底クラス。

    ドメイン層からインフラ層への依存を逆転させるためのインターフェース。
    具体的な実装はインフラ層で行う。
    """

    @abstractmethod
    async def save(self, document: Document) -> None:
        """文書を保存する。

        Args:
            document: 保存する文書

        Raises:
            Exception: 保存に失敗した場合
        """
        pass

    @abstractmethod
    async def find_by_id(self, document_id: DocumentId) -> Document | None:
        """IDで文書を検索する。

        Args:
            document_id: 検索する文書のID

        Returns:
            見つかった文書、存在しない場合はNone
        """
        pass

    @abstractmethod
    async def find_all(
        self, skip: int = 0, limit: int = 100, filter_: DocumentFilter | None = None
    ) -> tuple[list[DocumentListItem], int]:
        """文書一覧を取得する。

        Args:
            skip: スキップする件数
            limit: 取得する最大件数
            filter_: フィルター条件

        Returns:
            文書リストアイテムのリストと総件数のタプル
        """
        pass

    @abstractmethod
    async def update(self, document: Document) -> None:
        """文書を更新する。

        Args:
            document: 更新する文書

        Raises:
            DocumentNotFoundError: 文書が存在しない場合
            Exception: 更新に失敗した場合
        """
        pass

    @abstractmethod
    async def delete(self, document_id: DocumentId) -> None:
        """文書を削除する。

        Args:
            document_id: 削除する文書のID

        Raises:
            DocumentNotFoundError: 文書が存在しない場合
            Exception: 削除に失敗した場合
        """
        pass

    @abstractmethod
    async def exists(self, document_id: DocumentId) -> bool:
        """文書が存在するか確認する。

        Args:
            document_id: 確認する文書のID

        Returns:
            存在する場合はTrue、存在しない場合はFalse
        """
        pass

    @abstractmethod
    async def find_by_title(self, title: str) -> list[Document]:
        """タイトルで文書を検索する。

        Args:
            title: 検索するタイトル（部分一致）

        Returns:
            マッチする文書のリスト
        """
        pass

    @abstractmethod
    async def search_by_keyword(
        self,
        keyword: str,
        limit: int = 10,
        offset: int = 0,
    ) -> tuple[list[DocumentListItem], int]:
        """キーワードで文書を全文検索する。

        PostgreSQLの全文検索機能を使用して、文書のタイトルと内容を検索する。

        Args:
            keyword: 検索キーワード
            limit: 取得する最大件数
            offset: スキップする件数

        Returns:
            検索結果のリストと総件数のタプル
        """
        pass
