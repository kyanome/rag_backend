"""DocumentRepositoryの実装。"""

import base64
import uuid
from typing import Any, cast

from sqlalchemy import BinaryExpression, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.entities import Document
from src.domain.exceptions.document_exceptions import DocumentNotFoundError
from src.domain.repositories import DocumentRepository
from src.domain.value_objects import DocumentFilter, DocumentId, DocumentListItem

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
                # バイナリコンテンツはBase64エンコードして保存
                existing.content = base64.b64encode(document.content).decode("ascii") if document.content else ""  # type: ignore[assignment]
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
        # ベースクエリ
        base_query = select(DocumentModel)

        # フィルター条件の適用
        if filter_:
            conditions: list[BinaryExpression[bool]] = []

            # タイトルフィルター（部分一致、大文字小文字無視）
            if filter_.title:
                conditions.append(DocumentModel.title.ilike(f"%{filter_.title}%"))

            # 日付フィルター
            if filter_.created_from:
                conditions.append(
                    cast(
                        BinaryExpression[bool],
                        DocumentModel.created_at >= filter_.created_from,
                    )
                )
            if filter_.created_to:
                conditions.append(
                    cast(
                        BinaryExpression[bool],
                        DocumentModel.created_at <= filter_.created_to,
                    )
                )

            # カテゴリフィルター
            if filter_.category:
                # JSONフィールド内のcategoryを検索
                conditions.append(
                    cast(
                        BinaryExpression[bool],
                        func.json_extract(DocumentModel.document_metadata, "$.category")
                        == filter_.category,
                    )
                )

            # タグフィルター（いずれかに一致）
            if filter_.tags:
                tag_conditions = []
                for tag in filter_.tags:
                    # JSONフィールド内のtagsを検索（SQLiteの場合）
                    tag_conditions.append(
                        func.json_extract(
                            DocumentModel.document_metadata, "$.tags"
                        ).like(f'%"{tag}"%')
                    )
                if tag_conditions:
                    conditions.append(
                        cast(BinaryExpression[bool], or_(*tag_conditions))
                    )

            # すべての条件を適用
            if conditions:
                base_query = base_query.where(and_(*conditions))

        # 総件数の取得
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        # 文書の取得
        stmt = (
            base_query.offset(skip)
            .limit(limit)
            .order_by(DocumentModel.created_at.desc())
        )

        result = await self.session.execute(stmt)
        models = result.scalars().all()

        # DocumentListItemに変換
        items = []
        for model in models:
            metadata_dict: dict[str, Any] = model.document_metadata or {}  # type: ignore[assignment]
            item = DocumentListItem(
                id=DocumentId(value=str(model.id)),
                title=model.title,  # type: ignore[arg-type]
                file_name=metadata_dict.get("file_name", ""),
                file_size=metadata_dict.get("file_size", 0),
                content_type=metadata_dict.get("content_type", ""),
                category=metadata_dict.get("category"),
                tags=metadata_dict.get("tags", []),
                author=metadata_dict.get("author"),
                created_at=model.created_at,  # type: ignore[arg-type]
                updated_at=model.updated_at,  # type: ignore[arg-type]
            )
            items.append(item)

        return items, total

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
