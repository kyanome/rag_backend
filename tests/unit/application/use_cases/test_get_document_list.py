"""GetDocumentListUseCaseのテスト。"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.use_cases import (
    GetDocumentListInput,
    GetDocumentListOutput,
    GetDocumentListUseCase,
)
from src.domain.repositories import DocumentRepository
from src.domain.value_objects import (
    DocumentFilter,
    DocumentId,
    DocumentListItem,
)


class TestGetDocumentListUseCase:
    """GetDocumentListUseCaseのテストクラス。"""

    @pytest.fixture
    def mock_repository(self) -> MagicMock:
        """モックリポジトリを作成する。"""
        return MagicMock(spec=DocumentRepository)

    @pytest.fixture
    def use_case(self, mock_repository: MagicMock) -> GetDocumentListUseCase:
        """テスト対象のユースケースを作成する。"""
        return GetDocumentListUseCase(document_repository=mock_repository)

    def _create_test_item(self, **kwargs) -> DocumentListItem:
        """テスト用のDocumentListItemを作成する。"""
        defaults = {
            "id": DocumentId.generate(),
            "title": "test.pdf",
            "file_name": "test.pdf",
            "file_size": 1048576,
            "content_type": "application/pdf",
            "category": None,
            "tags": [],
            "author": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        defaults.update(kwargs)
        return DocumentListItem(**defaults)

    async def test_execute_with_default_parameters(
        self, use_case: GetDocumentListUseCase, mock_repository: MagicMock
    ) -> None:
        """デフォルトパラメータでの実行をテストする。"""
        # テストデータの準備
        test_items = [self._create_test_item(title=f"Document {i}") for i in range(3)]
        mock_repository.find_all = AsyncMock(return_value=(test_items, 3))

        # 実行
        input_dto = GetDocumentListInput()
        output = await use_case.execute(input_dto)

        # 検証
        assert isinstance(output, GetDocumentListOutput)
        assert len(output.documents) == 3
        assert output.page_info.page == 1
        assert output.page_info.page_size == 20
        assert output.page_info.total_count == 3
        assert output.page_info.total_pages == 1

        # リポジトリ呼び出しの検証
        mock_repository.find_all.assert_called_once_with(skip=0, limit=20, filter_=None)

    async def test_execute_with_pagination(
        self, use_case: GetDocumentListUseCase, mock_repository: MagicMock
    ) -> None:
        """ページネーションのテスト。"""
        # テストデータの準備
        test_items = [self._create_test_item(title=f"Document {i}") for i in range(5)]
        mock_repository.find_all = AsyncMock(return_value=(test_items, 50))

        # 実行（3ページ目、ページサイズ5）
        input_dto = GetDocumentListInput(page=3, page_size=5)
        output = await use_case.execute(input_dto)

        # 検証
        assert output.page_info.page == 3
        assert output.page_info.page_size == 5
        assert output.page_info.total_count == 50
        assert output.page_info.total_pages == 10
        assert output.page_info.has_next is True
        assert output.page_info.has_previous is True

        # リポジトリ呼び出しの検証（offset = (3-1) * 5 = 10）
        mock_repository.find_all.assert_called_once_with(skip=10, limit=5, filter_=None)

    async def test_execute_with_title_filter(
        self, use_case: GetDocumentListUseCase, mock_repository: MagicMock
    ) -> None:
        """タイトルフィルターのテスト。"""
        # テストデータの準備
        test_items = [
            self._create_test_item(title="技術仕様書.pdf"),
            self._create_test_item(title="技術ガイド.pdf"),
        ]
        mock_repository.find_all = AsyncMock(return_value=(test_items, 2))

        # 実行
        input_dto = GetDocumentListInput(title="技術")
        output = await use_case.execute(input_dto)

        # 検証
        assert len(output.documents) == 2

        # フィルター検証
        call_args = mock_repository.find_all.call_args
        filter_ = call_args.kwargs["filter_"]
        assert isinstance(filter_, DocumentFilter)
        assert filter_.title == "技術"

    async def test_execute_with_date_filter(
        self, use_case: GetDocumentListUseCase, mock_repository: MagicMock
    ) -> None:
        """日付フィルターのテスト。"""
        # テストデータの準備
        created_from = datetime(2024, 1, 1)
        created_to = datetime(2024, 12, 31)
        test_items = [self._create_test_item()]
        mock_repository.find_all = AsyncMock(return_value=(test_items, 1))

        # 実行
        input_dto = GetDocumentListInput(
            created_from=created_from, created_to=created_to
        )
        await use_case.execute(input_dto)

        # フィルター検証
        call_args = mock_repository.find_all.call_args
        filter_ = call_args.kwargs["filter_"]
        assert isinstance(filter_, DocumentFilter)
        assert filter_.created_from == created_from
        assert filter_.created_to == created_to

    async def test_execute_with_metadata_filter(
        self, use_case: GetDocumentListUseCase, mock_repository: MagicMock
    ) -> None:
        """メタデータフィルターのテスト。"""
        # テストデータの準備
        test_items = [
            self._create_test_item(
                category="技術文書",
                tags=["Python", "FastAPI"],
            )
        ]
        mock_repository.find_all = AsyncMock(return_value=(test_items, 1))

        # 実行
        input_dto = GetDocumentListInput(
            category="技術文書", tags=["Python", "FastAPI"]
        )
        await use_case.execute(input_dto)

        # フィルター検証
        call_args = mock_repository.find_all.call_args
        filter_ = call_args.kwargs["filter_"]
        assert isinstance(filter_, DocumentFilter)
        assert filter_.category == "技術文書"
        assert filter_.tags == ["Python", "FastAPI"]

    async def test_execute_with_tags_string_conversion(
        self, use_case: GetDocumentListUseCase, mock_repository: MagicMock
    ) -> None:
        """タグ文字列変換のテスト。"""
        # テストデータの準備
        test_items = []
        mock_repository.find_all = AsyncMock(return_value=(test_items, 0))

        # カンマ区切りのタグを含む入力
        input_dto = GetDocumentListInput(tags=["Python", "FastAPI", "async"])
        await use_case.execute(input_dto)

        # フィルター検証
        call_args = mock_repository.find_all.call_args
        filter_ = call_args.kwargs["filter_"]
        assert filter_.tags == ["Python", "FastAPI", "async"]

    async def test_execute_with_all_filters(
        self, use_case: GetDocumentListUseCase, mock_repository: MagicMock
    ) -> None:
        """すべてのフィルターを使用したテスト。"""
        # テストデータの準備
        test_items = []
        mock_repository.find_all = AsyncMock(return_value=(test_items, 0))

        # 実行
        input_dto = GetDocumentListInput(
            page=2,
            page_size=10,
            title="技術",
            created_from=datetime(2024, 1, 1),
            created_to=datetime(2024, 12, 31),
            category="技術文書",
            tags=["Python"],
        )
        output = await use_case.execute(input_dto)

        # ページネーション検証
        assert output.page_info.page == 2
        assert output.page_info.page_size == 10

        # フィルター検証
        call_args = mock_repository.find_all.call_args
        assert call_args.kwargs["skip"] == 10  # (2-1) * 10
        assert call_args.kwargs["limit"] == 10

        filter_ = call_args.kwargs["filter_"]
        assert filter_.title == "技術"
        assert filter_.category == "技術文書"
        assert filter_.tags == ["Python"]

    async def test_execute_with_empty_result(
        self, use_case: GetDocumentListUseCase, mock_repository: MagicMock
    ) -> None:
        """検索結果が空の場合のテスト。"""
        # テストデータの準備
        mock_repository.find_all = AsyncMock(return_value=([], 0))

        # 実行
        input_dto = GetDocumentListInput()
        output = await use_case.execute(input_dto)

        # 検証
        assert len(output.documents) == 0
        assert output.page_info.total_count == 0
        assert output.page_info.total_pages == 0
        assert output.page_info.has_next is False
        assert output.page_info.has_previous is False

    async def test_execute_with_repository_error(
        self, use_case: GetDocumentListUseCase, mock_repository: MagicMock
    ) -> None:
        """リポジトリエラーのテスト。"""
        # エラーの準備
        mock_repository.find_all = AsyncMock(
            side_effect=Exception("Database connection error")
        )

        # 実行と検証
        input_dto = GetDocumentListInput()
        with pytest.raises(Exception) as exc_info:
            await use_case.execute(input_dto)

        assert "Failed to get document list" in str(exc_info.value)
        assert "Database connection error" in str(exc_info.value)

    async def test_output_dto_conversion(
        self, use_case: GetDocumentListUseCase, mock_repository: MagicMock
    ) -> None:
        """出力DTOへの変換をテストする。"""
        # テストデータの準備
        created_at = datetime(2024, 1, 1, 12, 0, 0)
        updated_at = datetime(2024, 1, 2, 12, 0, 0)
        test_item = self._create_test_item(
            title="test.pdf",
            file_name="test.pdf",
            file_size=1048576,
            content_type="application/pdf",
            category="技術文書",
            tags=["PDF", "技術"],
            author="山田太郎",
            created_at=created_at,
            updated_at=updated_at,
        )
        mock_repository.find_all = AsyncMock(return_value=([test_item], 1))

        # 実行
        input_dto = GetDocumentListInput()
        output = await use_case.execute(input_dto)

        # 変換結果の検証
        assert len(output.documents) == 1
        doc = output.documents[0]
        assert doc.document_id == test_item.id.value
        assert doc.title == "test.pdf"
        assert doc.file_name == "test.pdf"
        assert doc.file_size == 1048576
        assert doc.content_type == "application/pdf"
        assert doc.category == "技術文書"
        assert doc.tags == ["PDF", "技術"]
        assert doc.author == "山田太郎"
        assert doc.created_at == created_at.isoformat()
        assert doc.updated_at == updated_at.isoformat()
