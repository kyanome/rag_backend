"""文書検索APIエンドポイントの統合テスト。"""

import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.application.use_cases.search_documents import (
    SearchDocumentsOutput,
    SearchDocumentsUseCase,
    SearchResultItemOutput,
)
from src.infrastructure.config.settings import Settings
from src.infrastructure.database.connection import create_all_tables, db_manager
from src.presentation.dependencies import get_search_documents_use_case
from src.presentation.main import app


@pytest.fixture
async def test_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncGenerator[Settings, None]:
    """テスト用の設定。"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # 一時ディレクトリを使用するように設定
        settings = Settings(file_storage_path=Path(temp_dir))
        settings.ensure_file_storage_path()
        yield settings


@pytest.fixture
async def client(test_settings: Settings) -> AsyncGenerator[AsyncClient, None]:
    """テスト用のHTTPクライアント。"""
    # データベースのテーブルを作成
    await create_all_tables()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

    # クリーンアップ
    await db_manager.close()
    # 依存性オーバーライドをクリア
    app.dependency_overrides.clear()


class TestSearchAPI:
    """検索APIの統合テスト。"""

    async def test_search_success_keyword(self, client: AsyncClient) -> None:
        """キーワード検索が成功する。"""
        # モックのユースケースを設定
        mock_use_case = AsyncMock(spec=SearchDocumentsUseCase)
        mock_use_case.execute.return_value = SearchDocumentsOutput(
            results=[
                SearchResultItemOutput(
                    document_id="doc-001",
                    document_title="テスト文書1",
                    content_preview="これはテスト文書の内容です",
                    score=0.95,
                    match_type="keyword",
                    confidence_level="high",
                    chunk_id=None,
                    chunk_index=None,
                    highlights=["<mark>テスト</mark>文書"],
                )
            ],
            total_count=1,
            search_time_ms=50.5,
            query_type="keyword",
            query_text="テスト",
            high_confidence_count=1,
        )

        # 依存性をオーバーライド
        app.dependency_overrides[get_search_documents_use_case] = lambda: mock_use_case

        # リクエスト
        response = await client.post(
            "/api/v1/search/",
            json={
                "query": "テスト",
                "search_type": "keyword",
                "limit": 10,
                "offset": 0,
            },
        )

        # 検証
        assert response.status_code == 200
        result = response.json()
        assert result["total_count"] == 1
        assert result["query_type"] == "keyword"
        assert result["query"] == "テスト"
        assert len(result["results"]) == 1
        assert result["results"][0]["document_title"] == "テスト文書1"
        assert result["results"][0]["match_type"] == "keyword"
        assert result["results"][0]["confidence_level"] == "high"
        assert result["page_info"]["page"] == 1
        assert result["page_info"]["page_size"] == 10
        assert result["page_info"]["total_pages"] == 1

    async def test_search_success_vector(self, client: AsyncClient) -> None:
        """ベクトル検索が成功する。"""
        # モックのユースケースを設定
        mock_use_case = AsyncMock(spec=SearchDocumentsUseCase)
        mock_use_case.execute.return_value = SearchDocumentsOutput(
            results=[
                SearchResultItemOutput(
                    document_id="doc-002",
                    document_title="技術文書",
                    content_preview="RAGシステムの実装について",
                    score=0.88,
                    match_type="vector",
                    confidence_level="medium",
                    chunk_id="chunk-001",
                    chunk_index=0,
                    highlights=[],
                )
            ],
            total_count=1,
            search_time_ms=120.3,
            query_type="vector",
            query_text="RAGシステム",
            high_confidence_count=0,
        )

        # 依存性をオーバーライド
        app.dependency_overrides[get_search_documents_use_case] = lambda: mock_use_case

        # リクエスト
        response = await client.post(
            "/api/v1/search/",
            json={
                "query": "RAGシステム",
                "search_type": "vector",
                "similarity_threshold": 0.8,
            },
        )

        # 検証
        assert response.status_code == 200
        result = response.json()
        assert result["query_type"] == "vector"
        assert result["results"][0]["match_type"] == "vector"
        assert result["results"][0]["chunk_id"] == "chunk-001"
        assert result["results"][0]["chunk_index"] == 0

    async def test_search_success_hybrid(self, client: AsyncClient) -> None:
        """ハイブリッド検索が成功する。"""
        # モックのユースケースを設定
        mock_use_case = AsyncMock(spec=SearchDocumentsUseCase)
        mock_use_case.execute.return_value = SearchDocumentsOutput(
            results=[
                SearchResultItemOutput(
                    document_id="doc-003",
                    document_title="統合文書",
                    content_preview="キーワードとベクトル両方でマッチ",
                    score=0.92,
                    match_type="both",
                    confidence_level="high",
                    chunk_id="chunk-002",
                    chunk_index=1,
                    highlights=["<mark>キーワード</mark>とベクトル"],
                )
            ],
            total_count=1,
            search_time_ms=180.7,
            query_type="hybrid",
            query_text="キーワード",
            high_confidence_count=1,
        )

        # 依存性をオーバーライド
        app.dependency_overrides[get_search_documents_use_case] = lambda: mock_use_case

        # リクエスト（デフォルトはhybrid）
        response = await client.post(
            "/api/v1/search/",
            json={"query": "キーワード"},
        )

        # 検証
        assert response.status_code == 200
        result = response.json()
        assert result["query_type"] == "hybrid"
        assert result["results"][0]["match_type"] == "both"

    async def test_search_with_pagination(self, client: AsyncClient) -> None:
        """ページネーションが正しく動作する。"""
        # モックのユースケースを設定
        mock_use_case = AsyncMock(spec=SearchDocumentsUseCase)
        mock_use_case.execute.return_value = SearchDocumentsOutput(
            results=[
                SearchResultItemOutput(
                    document_id=f"doc-{i:03d}",
                    document_title=f"文書{i}",
                    content_preview=f"内容{i}",
                    score=0.9 - i * 0.01,
                    match_type="keyword",
                    confidence_level="high",
                    chunk_id=None,
                    chunk_index=None,
                    highlights=[],
                )
                for i in range(5)
            ],
            total_count=50,
            search_time_ms=100.0,
            query_type="keyword",
            query_text="検索",
            high_confidence_count=30,
        )

        # 依存性をオーバーライド
        app.dependency_overrides[get_search_documents_use_case] = lambda: mock_use_case

        # リクエスト（2ページ目）
        response = await client.post(
            "/api/v1/search/",
            json={
                "query": "検索",
                "limit": 5,
                "offset": 5,
            },
        )

        # 検証
        assert response.status_code == 200
        result = response.json()
        assert len(result["results"]) == 5
        assert result["page_info"]["page"] == 2
        assert result["page_info"]["page_size"] == 5
        assert result["page_info"]["total_pages"] == 10
        assert result["page_info"]["total_count"] == 50

    async def test_search_invalid_search_type(self, client: AsyncClient) -> None:
        """無効な検索タイプでエラーになる。"""
        response = await client.post(
            "/api/v1/search/",
            json={
                "query": "テスト",
                "search_type": "invalid",
            },
        )

        assert response.status_code == 422  # Pydanticのバリデーションエラー
        result = response.json()
        assert "detail" in result

    async def test_search_empty_query(self, client: AsyncClient) -> None:
        """空のクエリでエラーになる。"""
        response = await client.post(
            "/api/v1/search/",
            json={
                "query": "",
            },
        )

        assert response.status_code == 422
        result = response.json()
        assert "detail" in result

    async def test_search_query_too_long(self, client: AsyncClient) -> None:
        """クエリが長すぎる場合エラーになる。"""
        response = await client.post(
            "/api/v1/search/",
            json={
                "query": "a" * 1001,  # 最大1000文字
            },
        )

        assert response.status_code == 422
        result = response.json()
        assert "detail" in result

    async def test_search_no_results(self, client: AsyncClient) -> None:
        """検索結果が0件の場合の処理。"""
        # モックのユースケースを設定
        mock_use_case = AsyncMock(spec=SearchDocumentsUseCase)
        mock_use_case.execute.return_value = SearchDocumentsOutput(
            results=[],
            total_count=0,
            search_time_ms=30.0,
            query_type="keyword",
            query_text="存在しない",
            high_confidence_count=0,
        )

        # 依存性をオーバーライド
        app.dependency_overrides[get_search_documents_use_case] = lambda: mock_use_case

        # リクエスト
        response = await client.post(
            "/api/v1/search/",
            json={"query": "存在しない"},
        )

        # 検証
        assert response.status_code == 200
        result = response.json()
        assert result["total_count"] == 0
        assert len(result["results"]) == 0
        assert result["page_info"]["total_pages"] == 0

    async def test_search_with_highlight_disabled(self, client: AsyncClient) -> None:
        """ハイライトを無効にした検索。"""
        # モックのユースケースを設定
        mock_use_case = AsyncMock(spec=SearchDocumentsUseCase)
        mock_use_case.execute.return_value = SearchDocumentsOutput(
            results=[
                SearchResultItemOutput(
                    document_id="doc-001",
                    document_title="テスト文書",
                    content_preview="テストの内容",
                    score=0.9,
                    match_type="keyword",
                    confidence_level="high",
                    chunk_id=None,
                    chunk_index=None,
                    highlights=[],
                )
            ],
            total_count=1,
            search_time_ms=40.0,
            query_type="keyword",
            query_text="テスト",
            high_confidence_count=1,
        )

        # 依存性をオーバーライド
        app.dependency_overrides[get_search_documents_use_case] = lambda: mock_use_case

        # リクエスト
        response = await client.post(
            "/api/v1/search/",
            json={
                "query": "テスト",
                "highlight": False,
            },
        )

        # 検証
        assert response.status_code == 200
        result = response.json()
        assert len(result["results"][0]["highlights"]) == 0

    async def test_search_use_case_error(self, client: AsyncClient) -> None:
        """ユースケースでエラーが発生した場合。"""
        # モックのユースケースを設定（例外を発生させる）
        mock_use_case = AsyncMock(spec=SearchDocumentsUseCase)
        mock_use_case.execute.side_effect = Exception("データベースエラー")

        # 依存性をオーバーライド
        app.dependency_overrides[get_search_documents_use_case] = lambda: mock_use_case

        # リクエスト
        response = await client.post(
            "/api/v1/search/",
            json={"query": "テスト"},
        )

        # 検証
        assert response.status_code == 500
        result = response.json()
        assert "検索処理中にエラーが発生しました" in result["detail"]

    async def test_search_invalid_parameters(self, client: AsyncClient) -> None:
        """無効なパラメータでエラーになる。"""
        # limitが範囲外
        response = await client.post(
            "/api/v1/search/",
            json={
                "query": "テスト",
                "limit": 101,  # 最大100
            },
        )
        assert response.status_code == 422

        # offsetが負の値
        response = await client.post(
            "/api/v1/search/",
            json={
                "query": "テスト",
                "offset": -1,
            },
        )
        assert response.status_code == 422

        # similarity_thresholdが範囲外
        response = await client.post(
            "/api/v1/search/",
            json={
                "query": "テスト",
                "similarity_threshold": 1.5,  # 最大1.0
            },
        )
        assert response.status_code == 422
