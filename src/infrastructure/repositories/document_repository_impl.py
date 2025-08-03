"""DocumentRepositoryの実装。"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.entities import Document
from src.domain.exceptions import DocumentNotFoundError
from src.domain.repositories import DocumentRepository
from src.domain.value_objects import DocumentId

from ..database.models import DocumentChunkModel, DocumentModel
from ..externals.file_storage import FileStorageService


class DocumentRepositoryImpl(DocumentRepository):
    """DocumentRepositoryの具体的な実装。

    SQLAlchemyとファイルストレージを使用して文書の永続化を行う。
    """

    def __init__(self, session: AsyncSession, file_storage: FileStorageService) -> None:
        """リポジトリを初期化する。

        Args:
            session: データベースセッション
            file_storage: ファイルストレージサービス
        """
        self.session = session
        self.file_storage = file_storage

    async def save(self, document: Document) -> None:
        """文書を保存する。

        Args:
            document: 保存する文書

        Raises:
            Exception: 保存に失敗した場合
        """
        try:
            # ファイルの保存
            if document.content:
                file_path = await self.file_storage.save(
                    document_id=document.id.value,
                    file_name=document.metadata.file_name,
                    content=document.content,
                )
            else:
                file_path = None

            # 既存のレコードを確認
            existing = await self.session.get(
                DocumentModel, uuid.UUID(document.id.value)
            )

            if existing:
                # 更新の場合
                existing.title = document.title  # type: ignore[assignment]
                existing.content = document.content.decode("utf-8") if document.content else ""  # type: ignore[assignment]
                existing.document_metadata = {  # type: ignore[assignment]
                    "file_name": document.metadata.file_name,
                    "file_size": document.metadata.file_size,
                    "content_type": document.metadata.content_type,
                    "category": document.metadata.category,
                    "tags": document.metadata.tags,
                    "author": document.metadata.author,
                    "description": document.metadata.description,
                }
                existing.version = document.version  # type: ignore[assignment]
                existing.updated_at = document.metadata.updated_at  # type: ignore[assignment]
                if file_path:
                    existing.file_path = file_path  # type: ignore[assignment]

                # 既存のチャンクを削除
                stmt = select(DocumentChunkModel).where(
                    DocumentChunkModel.document_id == existing.id
                )
                result = await self.session.execute(stmt)
                chunks = result.scalars().all()
                for chunk in chunks:
                    await self.session.delete(chunk)

                # 新しいチャンクを追加
                for domain_chunk in document.chunks:
                    chunk_model = DocumentChunkModel.from_domain(domain_chunk)
                    existing.chunks.append(chunk_model)
            else:
                # 新規作成の場合
                model = DocumentModel.from_domain(document)
                if file_path:
                    model.file_path = file_path  # type: ignore[assignment]

                # チャンクの追加
                for domain_chunk in document.chunks:
                    chunk_model = DocumentChunkModel.from_domain(domain_chunk)
                    model.chunks.append(chunk_model)

                self.session.add(model)

            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise Exception(f"Failed to save document: {e}") from e

    async def find_by_id(self, document_id: DocumentId) -> Document | None:
        """IDで文書を検索する。

        Args:
            document_id: 検索する文書のID

        Returns:
            見つかった文書、存在しない場合はNone
        """
        stmt = (
            select(DocumentModel)
            .where(DocumentModel.id == uuid.UUID(document_id.value))
            .options(selectinload(DocumentModel.chunks))
        )

        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return model.to_domain()

    async def find_all(
        self, skip: int = 0, limit: int = 100
    ) -> tuple[list[Document], int]:
        """すべての文書を取得する。

        Args:
            skip: スキップする件数
            limit: 取得する最大件数

        Returns:
            文書のリストと総件数のタプル
        """
        # 総件数の取得
        count_stmt = select(func.count()).select_from(DocumentModel)
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        # 文書の取得
        stmt = (
            select(DocumentModel)
            .options(selectinload(DocumentModel.chunks))
            .offset(skip)
            .limit(limit)
            .order_by(DocumentModel.created_at.desc())
        )

        result = await self.session.execute(stmt)
        models = result.scalars().all()

        documents = [model.to_domain() for model in models]
        return documents, total

    async def update(self, document: Document) -> None:
        """文書を更新する。

        Args:
            document: 更新する文書

        Raises:
            DocumentNotFoundError: 文書が存在しない場合
            Exception: 更新に失敗した場合
        """
        existing = await self.find_by_id(document.id)
        if existing is None:
            raise DocumentNotFoundError(document.id.value)

        # バージョンを増やして保存
        document.increment_version()
        await self.save(document)

    async def delete(self, document_id: DocumentId) -> None:
        """文書を削除する。

        Args:
            document_id: 削除する文書のID

        Raises:
            DocumentNotFoundError: 文書が存在しない場合
            Exception: 削除に失敗した場合
        """
        try:
            model = await self.session.get(DocumentModel, uuid.UUID(document_id.value))
            if model is None:
                raise DocumentNotFoundError(document_id.value)

            # ファイルの削除
            if model.file_path:
                try:
                    await self.file_storage.delete(model.file_path)  # type: ignore[arg-type]
                except FileNotFoundError:
                    # ファイルが既に存在しない場合は無視
                    pass

            # レコードの削除（チャンクもカスケード削除される）
            await self.session.delete(model)
            await self.session.commit()
        except DocumentNotFoundError:
            raise
        except Exception as e:
            await self.session.rollback()
            raise Exception(f"Failed to delete document: {e}") from e

    async def exists(self, document_id: DocumentId) -> bool:
        """文書が存在するか確認する。

        Args:
            document_id: 確認する文書のID

        Returns:
            存在する場合はTrue、存在しない場合はFalse
        """
        stmt = select(DocumentModel.id).where(
            DocumentModel.id == uuid.UUID(document_id.value)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def find_by_title(self, title: str) -> list[Document]:
        """タイトルで文書を検索する。

        Args:
            title: 検索するタイトル（部分一致）

        Returns:
            マッチする文書のリスト
        """
        stmt = (
            select(DocumentModel)
            .where(DocumentModel.title.ilike(f"%{title}%"))
            .options(selectinload(DocumentModel.chunks))
            .order_by(DocumentModel.created_at.desc())
        )

        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [model.to_domain() for model in models]
