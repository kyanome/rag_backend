"""文書一覧取得ユースケース。"""

from datetime import datetime
from typing import Self

from pydantic import BaseModel, Field, model_validator

from ...domain.repositories import DocumentRepository
from ...domain.value_objects import DocumentFilter, DocumentListItem, PageInfo


class GetDocumentListInput(BaseModel):
    """文書一覧取得の入力DTO。

    Attributes:
        page: ページ番号（1から開始）
        page_size: 1ページあたりの件数
        title: タイトル検索キーワード（部分一致）
        created_from: 作成日時の開始
        created_to: 作成日時の終了
        category: カテゴリ
        tags: タグリスト（いずれかに一致）
    """

    page: int = Field(default=1, ge=1, description="ページ番号（1から開始）")
    page_size: int = Field(
        default=20, ge=1, le=100, description="1ページあたりの件数（最大100）"
    )
    title: str | None = Field(
        default=None, description="タイトル検索キーワード（部分一致）"
    )
    created_from: datetime | None = Field(default=None, description="作成日時の開始")
    created_to: datetime | None = Field(default=None, description="作成日時の終了")
    category: str | None = Field(default=None, description="カテゴリ")
    tags: list[str] | None = Field(
        default=None, description="タグリスト（いずれかに一致）"
    )

    @model_validator(mode="after")
    def validate_dates(self) -> Self:
        """日付の妥当性を検証する。"""
        if (
            self.created_to
            and self.created_from
            and self.created_to < self.created_from
        ):
            raise ValueError("created_to must be after or equal to created_from")
        return self


class DocumentListItemOutput(BaseModel):
    """文書リストアイテムの出力DTO。

    Attributes:
        document_id: 文書ID
        title: 文書タイトル
        file_name: ファイル名
        file_size: ファイルサイズ（バイト）
        content_type: コンテンツタイプ
        category: カテゴリ
        tags: タグリスト
        author: 作成者
        created_at: 作成日時（ISO形式）
        updated_at: 更新日時（ISO形式）
    """

    document_id: str = Field(..., description="文書ID")
    title: str = Field(..., description="文書タイトル")
    file_name: str = Field(..., description="ファイル名")
    file_size: int = Field(..., description="ファイルサイズ（バイト）")
    content_type: str = Field(..., description="コンテンツタイプ")
    category: str | None = Field(None, description="カテゴリ")
    tags: list[str] = Field(default_factory=list, description="タグリスト")
    author: str | None = Field(None, description="作成者")
    created_at: str = Field(..., description="作成日時（ISO形式）")
    updated_at: str = Field(..., description="更新日時（ISO形式）")

    @classmethod
    def from_domain(cls, item: DocumentListItem) -> "DocumentListItemOutput":
        """ドメインモデルから出力DTOを作成する。

        Args:
            item: 文書リストアイテム

        Returns:
            出力DTO
        """
        return cls(
            document_id=item.id.value,
            title=item.title,
            file_name=item.file_name,
            file_size=item.file_size,
            content_type=item.content_type,
            category=item.category,
            tags=item.tags,
            author=item.author,
            created_at=item.created_at.isoformat(),
            updated_at=item.updated_at.isoformat(),
        )


class GetDocumentListOutput(BaseModel):
    """文書一覧取得の出力DTO。

    Attributes:
        documents: 文書リスト
        page_info: ページ情報
    """

    documents: list[DocumentListItemOutput] = Field(..., description="文書リスト")
    page_info: PageInfo = Field(..., description="ページ情報")


class GetDocumentListUseCase:
    """文書一覧取得ユースケース。

    文書の一覧をページネーションとフィルタリングをサポートして取得する。
    """

    def __init__(self, document_repository: DocumentRepository) -> None:
        """ユースケースを初期化する。

        Args:
            document_repository: 文書リポジトリ
        """
        self._document_repository = document_repository

    async def execute(self, input_dto: GetDocumentListInput) -> GetDocumentListOutput:
        """文書一覧を取得する。

        Args:
            input_dto: 入力DTO

        Returns:
            出力DTO

        Raises:
            ValueError: 入力値が不正な場合
            Exception: 文書一覧の取得に失敗した場合
        """
        # フィルター条件を作成
        filter_ = None
        if any(
            [
                input_dto.title,
                input_dto.created_from,
                input_dto.created_to,
                input_dto.category,
                input_dto.tags,
            ]
        ):
            filter_ = DocumentFilter(
                title=input_dto.title,
                created_from=input_dto.created_from,
                created_to=input_dto.created_to,
                category=input_dto.category,
                tags=input_dto.tags,
            )

        # オフセット計算
        offset = (input_dto.page - 1) * input_dto.page_size

        try:
            # リポジトリから文書一覧を取得
            items, total_count = await self._document_repository.find_all(
                skip=offset, limit=input_dto.page_size, filter_=filter_
            )

            # ページ情報を作成
            page_info = PageInfo.create(
                page=input_dto.page,
                page_size=input_dto.page_size,
                total_count=total_count,
            )

            # 出力DTOに変換
            document_outputs = [
                DocumentListItemOutput.from_domain(item) for item in items
            ]

            return GetDocumentListOutput(
                documents=document_outputs, page_info=page_info
            )

        except Exception as e:
            raise Exception(f"Failed to get document list: {e}") from e
