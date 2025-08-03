"""文書更新ユースケース。"""

from typing import Self

from pydantic import BaseModel, Field, model_validator

from ...domain.entities import Document
from ...domain.exceptions.document_exceptions import (
    DocumentNotFoundError,
    DocumentValidationError,
)
from ...domain.repositories import DocumentRepository
from ...domain.value_objects import DocumentId


class UpdateDocumentInput(BaseModel):
    """文書更新の入力DTO。

    Attributes:
        document_id: 更新する文書のID
        title: 文書タイトル
        category: カテゴリ
        tags: タグリスト
        author: 作成者
        description: 文書の説明
    """

    document_id: str = Field(..., description="更新する文書のID")
    title: str | None = Field(None, description="文書タイトル")
    category: str | None = Field(None, description="カテゴリ")
    tags: list[str] | None = Field(None, description="タグリスト")
    author: str | None = Field(None, description="作成者")
    description: str | None = Field(None, description="文書の説明")

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> Self:
        """少なくとも1つの更新フィールドが指定されていることを検証する。"""
        update_fields = [
            self.title,
            self.category,
            self.tags,
            self.author,
            self.description,
        ]
        if not any(field is not None for field in update_fields):
            raise ValueError("At least one field must be provided for update")
        return self


class UpdateDocumentOutput(BaseModel):
    """文書更新の出力DTO。

    Attributes:
        document_id: 文書ID
        title: 文書タイトル
        file_name: ファイル名
        file_size: ファイルサイズ（バイト）
        content_type: コンテンツタイプ
        category: カテゴリ
        tags: タグリスト
        author: 作成者
        description: 文書の説明
        created_at: 作成日時（ISO形式）
        updated_at: 更新日時（ISO形式）
        version: バージョン番号
    """

    document_id: str = Field(..., description="文書ID")
    title: str = Field(..., description="文書タイトル")
    file_name: str = Field(..., description="ファイル名")
    file_size: int = Field(..., description="ファイルサイズ（バイト）")
    content_type: str = Field(..., description="コンテンツタイプ")
    category: str | None = Field(None, description="カテゴリ")
    tags: list[str] = Field(default_factory=list, description="タグリスト")
    author: str | None = Field(None, description="作成者")
    description: str | None = Field(None, description="文書の説明")
    created_at: str = Field(..., description="作成日時（ISO形式）")
    updated_at: str = Field(..., description="更新日時（ISO形式）")
    version: int = Field(..., description="バージョン番号")

    @classmethod
    def from_domain(cls, document: Document) -> "UpdateDocumentOutput":
        """ドメインモデルから出力DTOを作成する。

        Args:
            document: 文書エンティティ

        Returns:
            出力DTO
        """
        return cls(
            document_id=document.id.value,
            title=document.title,
            file_name=document.metadata.file_name,
            file_size=document.metadata.file_size,
            content_type=document.metadata.content_type,
            category=document.metadata.category,
            tags=document.metadata.tags,
            author=document.metadata.author,
            description=document.metadata.description,
            created_at=document.metadata.created_at.isoformat(),
            updated_at=document.metadata.updated_at.isoformat(),
            version=document.version,
        )


class UpdateDocumentUseCase:
    """文書更新ユースケース。

    指定されたIDの文書のメタデータを更新する。
    """

    def __init__(self, document_repository: DocumentRepository) -> None:
        """ユースケースを初期化する。

        Args:
            document_repository: 文書リポジトリ
        """
        self._document_repository = document_repository

    async def execute(self, input_dto: UpdateDocumentInput) -> UpdateDocumentOutput:
        """文書を更新する。

        Args:
            input_dto: 入力DTO

        Returns:
            出力DTO

        Raises:
            DocumentNotFoundError: 文書が見つからない場合
            DocumentValidationError: バリデーションエラーの場合
            Exception: 文書の更新に失敗した場合
        """
        try:
            # 文書IDの値オブジェクトを作成
            document_id = DocumentId(value=input_dto.document_id)

            # リポジトリから文書を取得
            document = await self._document_repository.find_by_id(document_id)

            if document is None:
                raise DocumentNotFoundError(input_dto.document_id)

            # 更新フィールドを適用
            if input_dto.title is not None:
                document.title = input_dto.title

            # メタデータの更新
            metadata_updates: dict[str, str | list[str] | None] = {}
            if input_dto.category is not None:
                metadata_updates["category"] = input_dto.category
            if input_dto.tags is not None:
                metadata_updates["tags"] = input_dto.tags
            if input_dto.author is not None:
                metadata_updates["author"] = input_dto.author
            if input_dto.description is not None:
                metadata_updates["description"] = input_dto.description

            if metadata_updates:
                # 既存のメタデータを更新
                document.metadata = document.metadata.model_copy(
                    update=metadata_updates
                )

            # リポジトリで更新（バージョンが自動的にインクリメントされる）
            await self._document_repository.update(document)

            # 更新後の文書を再取得（バージョンが更新されている）
            updated_document = await self._document_repository.find_by_id(document_id)
            if updated_document is None:
                raise Exception("Failed to retrieve updated document")

            # 出力DTOに変換
            return UpdateDocumentOutput.from_domain(updated_document)

        except (DocumentNotFoundError, DocumentValidationError):
            raise
        except Exception as e:
            raise Exception(f"Failed to update document: {e}") from e
