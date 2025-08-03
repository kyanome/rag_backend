"""文書詳細取得ユースケース。"""

from pydantic import BaseModel, Field

from ...domain.entities import Document
from ...domain.exceptions.document_exceptions import DocumentNotFoundError
from ...domain.repositories import DocumentRepository
from ...domain.value_objects import DocumentId


class GetDocumentInput(BaseModel):
    """文書詳細取得の入力DTO。

    Attributes:
        document_id: 取得する文書のID
    """

    document_id: str = Field(..., description="取得する文書のID")


class GetDocumentOutput(BaseModel):
    """文書詳細取得の出力DTO。

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
    def from_domain(cls, document: Document) -> "GetDocumentOutput":
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


class GetDocumentUseCase:
    """文書詳細取得ユースケース。

    指定されたIDの文書の詳細情報を取得する。
    """

    def __init__(self, document_repository: DocumentRepository) -> None:
        """ユースケースを初期化する。

        Args:
            document_repository: 文書リポジトリ
        """
        self._document_repository = document_repository

    async def execute(self, input_dto: GetDocumentInput) -> GetDocumentOutput:
        """文書詳細を取得する。

        Args:
            input_dto: 入力DTO

        Returns:
            出力DTO

        Raises:
            DocumentNotFoundError: 文書が見つからない場合
            Exception: 文書の取得に失敗した場合
        """
        try:
            # 文書IDの値オブジェクトを作成
            document_id = DocumentId(value=input_dto.document_id)

            # リポジトリから文書を取得
            document = await self._document_repository.find_by_id(document_id)

            if document is None:
                raise DocumentNotFoundError(input_dto.document_id)

            # 出力DTOに変換
            return GetDocumentOutput.from_domain(document)

        except DocumentNotFoundError:
            raise
        except Exception as e:
            raise Exception(f"Failed to get document: {e}") from e
