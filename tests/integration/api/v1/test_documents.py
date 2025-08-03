"""文書APIエンドポイントの統合テスト。"""

import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from src.infrastructure.config.settings import Settings
from src.infrastructure.database.connection import create_all_tables, db_manager
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


class TestDocumentUploadAPI:
    """文書アップロードAPIの統合テスト。"""

    async def test_upload_document_success(self, client: AsyncClient) -> None:
        """文書のアップロードが成功する。"""
        # テストファイル
        files = {"file": ("test.pdf", b"test pdf content", "application/pdf")}
        data = {
            "title": "Test Document",
            "category": "Test Category",
            "tags": "tag1,tag2,tag3",
            "author": "Test Author",
            "description": "Test Description",
        }

        # リクエスト
        response = await client.post("/api/v1/documents/", files=files, data=data)

        # 検証
        assert response.status_code == 201
        result = response.json()
        assert result["title"] == "Test Document"
        assert result["file_name"] == "test.pdf"
        assert result["file_size"] == len(b"test pdf content")
        assert result["content_type"] == "application/pdf"
        assert "document_id" in result
        assert "created_at" in result

    async def test_upload_document_minimal_input(self, client: AsyncClient) -> None:
        """最小限の入力で文書をアップロードできる。"""
        # テストファイル（必須フィールドのみ）
        files = {"file": ("minimal.txt", b"minimal content", "text/plain")}

        # リクエスト
        response = await client.post("/api/v1/documents/", files=files)

        # 検証
        assert response.status_code == 201
        result = response.json()
        assert result["title"] == "minimal.txt"
        assert result["file_name"] == "minimal.txt"
        assert result["content_type"] == "text/plain"

    async def test_upload_document_with_large_file(self, client: AsyncClient) -> None:
        """大きすぎるファイルのアップロードは拒否される。"""
        # 100MB + 1バイトのファイル
        large_content = b"x" * (100 * 1024 * 1024 + 1)
        files = {"file": ("large.pdf", large_content, "application/pdf")}

        # リクエスト
        response = await client.post("/api/v1/documents/", files=files)

        # 検証
        assert response.status_code == 413
        assert "exceeds maximum allowed size" in response.json()["detail"]

    async def test_upload_document_with_unsupported_type(
        self, client: AsyncClient
    ) -> None:
        """サポートされていないファイルタイプは拒否される。"""
        # 実行ファイル
        files = {
            "file": ("test.exe", b"executable content", "application/x-msdownload")
        }

        # リクエスト
        response = await client.post("/api/v1/documents/", files=files)

        # 検証
        assert response.status_code == 400
        assert "Unsupported content type" in response.json()["detail"]

    async def test_upload_document_with_various_supported_types(
        self, client: AsyncClient
    ) -> None:
        """サポートされている各種ファイルタイプをアップロードできる。"""
        test_cases = [
            ("test.pdf", "application/pdf"),
            (
                "test.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
            ("test.doc", "application/msword"),
            ("test.txt", "text/plain"),
            ("test.csv", "text/csv"),
            ("test.md", "text/markdown"),
        ]

        for file_name, content_type in test_cases:
            files = {"file": (file_name, b"test content", content_type)}

            response = await client.post("/api/v1/documents/", files=files)
            assert response.status_code == 201, f"Failed for {content_type}"
            result = response.json()
            assert result["content_type"] == content_type

    async def test_upload_document_with_tags_parsing(self, client: AsyncClient) -> None:
        """タグが正しく解析される。"""
        files = {"file": ("test.txt", b"content", "text/plain")}
        data = {
            "tags": "  tag1  , tag2,  tag3  ,,,",  # 空白とカンマのテスト
        }

        response = await client.post("/api/v1/documents/", files=files, data=data)
        assert response.status_code == 201

    async def test_health_check(self, client: AsyncClient) -> None:
        """ヘルスチェックエンドポイントが動作する。"""
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    async def test_root_endpoint(self, client: AsyncClient) -> None:
        """ルートエンドポイントが動作する。"""
        response = await client.get("/")
        assert response.status_code == 200
        result = response.json()
        assert result["message"] == "RAG Backend API"
        assert result["version"] == "0.1.0"
