"""文書削除ユースケース。"""

from pydantic import BaseModel, Field

from ...domain.exceptions.document_exceptions import DocumentNotFoundError
from ...domain.repositories import DocumentRepository
from ...domain.value_objects import DocumentId


class DeleteDocumentInput(BaseModel):
    """文書削除の入力DTO。

    Attributes:
        document_id: 削除する文書のID
    """

    document_id: str = Field(..., description="削除する文書のID")


class DeleteDocumentUseCase:
    """文書削除ユースケース。

    指定されたIDの文書を削除する。
    """

    def __init__(self, document_repository: DocumentRepository) -> None:
        """ユースケースを初期化する。

        Args:
            document_repository: 文書リポジトリ
        """
        self._document_repository = document_repository

    async def execute(self, input_dto: DeleteDocumentInput) -> None:
        """文書を削除する。

        Args:
            input_dto: 入力DTO

        Raises:
            DocumentNotFoundError: 文書が見つからない場合
            Exception: 文書の削除に失敗した場合
        """
        try:
            # 文書IDの値オブジェクトを作成
            document_id = DocumentId(value=input_dto.document_id)

            # 文書の存在確認
            exists = await self._document_repository.exists(document_id)
            if not exists:
                raise DocumentNotFoundError(input_dto.document_id)

            # リポジトリから文書を削除
            await self._document_repository.delete(document_id)

        except DocumentNotFoundError:
            raise
        except Exception as e:
            raise Exception(f"Failed to delete document: {e}") from e
