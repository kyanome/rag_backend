"""文書APIエンドポイントの統合テスト。"""

import tempfile
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta
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


class TestDocumentListAPI:
    """文書一覧取得APIの統合テスト。"""

    async def _create_test_documents(
        self, client: AsyncClient, count: int = 5
    ) -> list[str]:
        """テスト用の文書を作成する。"""
        document_ids = []
        for i in range(count):
            files = {
                "file": (f"test{i}.pdf", f"content {i}".encode(), "application/pdf")
            }
            data = {
                "title": f"Test Document {i}",
                "category": "技術文書" if i % 2 == 0 else "営業資料",
                "tags": f"tag{i},common",
                "author": f"Author {i}",
                "description": f"Description {i}",
            }
            response = await client.post("/api/v1/documents/", files=files, data=data)
            assert response.status_code == 201
            document_ids.append(response.json()["document_id"])
        return document_ids

    async def test_get_document_list_default(self, client: AsyncClient) -> None:
        """デフォルトパラメータで文書一覧を取得できる。"""
        # テストデータ作成
        await self._create_test_documents(client, 5)

        # 一覧取得
        response = await client.get("/api/v1/documents/")

        # 検証
        assert response.status_code == 200
        result = response.json()
        assert "documents" in result
        assert "page_info" in result

        # ページ情報の検証
        page_info = result["page_info"]
        assert page_info["page"] == 1
        assert page_info["page_size"] == 20
        assert page_info["total_count"] == 5
        assert page_info["total_pages"] == 1

        # 文書リストの検証
        documents = result["documents"]
        assert len(documents) == 5

        # 最新の文書が最初に来ることを確認（作成日時降順）
        for i in range(len(documents) - 1):
            assert documents[i]["created_at"] >= documents[i + 1]["created_at"]

    async def test_get_document_list_with_pagination(self, client: AsyncClient) -> None:
        """ページネーションが正しく動作する。"""
        # 15件のテストデータ作成
        await self._create_test_documents(client, 15)

        # 1ページ目（サイズ10）
        response = await client.get(
            "/api/v1/documents/", params={"page": 1, "page_size": 10}
        )
        assert response.status_code == 200
        result = response.json()
        assert len(result["documents"]) == 10
        assert result["page_info"]["page"] == 1
        assert result["page_info"]["page_size"] == 10
        assert result["page_info"]["total_count"] == 15
        assert result["page_info"]["total_pages"] == 2

        # 2ページ目（サイズ10）
        response = await client.get(
            "/api/v1/documents/", params={"page": 2, "page_size": 10}
        )
        assert response.status_code == 200
        result = response.json()
        assert len(result["documents"]) == 5
        assert result["page_info"]["page"] == 2

    async def test_get_document_list_with_title_filter(
        self, client: AsyncClient
    ) -> None:
        """タイトルフィルターが正しく動作する。"""
        # テストデータ作成
        files1 = {"file": ("spec.pdf", b"content", "application/pdf")}
        data1 = {"title": "技術仕様書"}
        await client.post("/api/v1/documents/", files=files1, data=data1)

        files2 = {"file": ("guide.pdf", b"content", "application/pdf")}
        data2 = {"title": "技術ガイド"}
        await client.post("/api/v1/documents/", files=files2, data=data2)

        files3 = {"file": ("sales.pdf", b"content", "application/pdf")}
        data3 = {"title": "営業報告書"}
        await client.post("/api/v1/documents/", files=files3, data=data3)

        # タイトルでフィルタリング
        response = await client.get("/api/v1/documents/", params={"title": "技術"})

        assert response.status_code == 200
        result = response.json()
        assert result["page_info"]["total_count"] == 2

        titles = [doc["title"] for doc in result["documents"]]
        assert "技術仕様書" in titles
        assert "技術ガイド" in titles
        assert "営業報告書" not in titles

    async def test_get_document_list_with_category_filter(
        self, client: AsyncClient
    ) -> None:
        """カテゴリフィルターが正しく動作する。"""
        # テストデータ作成（カテゴリ別）
        await self._create_test_documents(client, 10)

        # カテゴリでフィルタリング
        response = await client.get(
            "/api/v1/documents/", params={"category": "技術文書"}
        )

        assert response.status_code == 200
        result = response.json()

        # 偶数インデックスの文書のみ（0, 2, 4, 6, 8）
        assert result["page_info"]["total_count"] == 5
        assert all(doc["category"] == "技術文書" for doc in result["documents"])

    async def test_get_document_list_with_tags_filter(
        self, client: AsyncClient
    ) -> None:
        """タグフィルターが正しく動作する。"""
        # テストデータ作成
        files1 = {"file": ("python.pdf", b"content", "application/pdf")}
        data1 = {"tags": "Python,プログラミング"}
        await client.post("/api/v1/documents/", files=files1, data=data1)

        files2 = {"file": ("fastapi.pdf", b"content", "application/pdf")}
        data2 = {"tags": "Python,FastAPI,Web"}
        await client.post("/api/v1/documents/", files=files2, data=data2)

        files3 = {"file": ("java.pdf", b"content", "application/pdf")}
        data3 = {"tags": "Java,プログラミング"}
        await client.post("/api/v1/documents/", files=files3, data=data3)

        # タグでフィルタリング（カンマ区切り）
        response = await client.get("/api/v1/documents/", params={"tags": "Python,Web"})

        assert response.status_code == 200
        result = response.json()
        assert result["page_info"]["total_count"] == 2

    async def test_get_document_list_with_date_filter(
        self, client: AsyncClient
    ) -> None:
        """日付フィルターが正しく動作する。"""
        # テストデータ作成
        await self._create_test_documents(client, 5)

        # 現在時刻の前後でフィルタリング
        now = datetime.now()
        created_from = (now - timedelta(hours=1)).isoformat()
        created_to = (now + timedelta(hours=1)).isoformat()

        response = await client.get(
            "/api/v1/documents/",
            params={"created_from": created_from, "created_to": created_to},
        )

        assert response.status_code == 200
        result = response.json()
        # 1時間以内に作成されたものが取得される
        assert result["page_info"]["total_count"] == 5

    async def test_get_document_list_with_combined_filters(
        self, client: AsyncClient
    ) -> None:
        """複合フィルターが正しく動作する。"""
        # テストデータ作成
        await self._create_test_documents(client, 10)

        # 複合フィルター（カテゴリ + ページネーション）
        response = await client.get(
            "/api/v1/documents/",
            params={"category": "技術文書", "page": 1, "page_size": 3},
        )

        assert response.status_code == 200
        result = response.json()
        assert len(result["documents"]) == 3
        assert result["page_info"]["total_count"] == 5
        assert result["page_info"]["total_pages"] == 2

    async def test_get_document_list_empty_result(self, client: AsyncClient) -> None:
        """検索結果が空の場合の動作を確認する。"""
        # データなしで検索
        response = await client.get(
            "/api/v1/documents/", params={"title": "存在しない文書"}
        )

        assert response.status_code == 200
        result = response.json()
        assert len(result["documents"]) == 0
        assert result["page_info"]["total_count"] == 0
        assert result["page_info"]["total_pages"] == 0

    async def test_get_document_list_invalid_page(self, client: AsyncClient) -> None:
        """無効なページ番号でエラーになる。"""
        response = await client.get("/api/v1/documents/", params={"page": 0})
        assert response.status_code == 422  # バリデーションエラー

    async def test_get_document_list_invalid_page_size(
        self, client: AsyncClient
    ) -> None:
        """無効なページサイズでエラーになる。"""
        # ページサイズが上限を超える
        response = await client.get("/api/v1/documents/", params={"page_size": 101})
        assert response.status_code == 422  # バリデーションエラー

        # ページサイズが0
        response = await client.get("/api/v1/documents/", params={"page_size": 0})
        assert response.status_code == 422  # バリデーションエラー

    async def test_get_document_list_invalid_date_range(
        self, client: AsyncClient
    ) -> None:
        """無効な日付範囲でエラーになる。"""
        created_from = "2024-12-31T00:00:00"
        created_to = "2024-01-01T00:00:00"  # fromより前

        response = await client.get(
            "/api/v1/documents/",
            params={"created_from": created_from, "created_to": created_to},
        )

        assert response.status_code == 400
        assert (
            "created_to must be after or equal to created_from"
            in response.json()["detail"]
        )

    async def test_get_document_list_response_format(self, client: AsyncClient) -> None:
        """レスポンスフォーマットが正しいことを確認する。"""
        # テストデータ作成
        files = {"file": ("test.pdf", b"content", "application/pdf")}
        data = {
            "title": "Test Document",
            "category": "Test Category",
            "tags": "tag1,tag2",
            "author": "Test Author",
            "description": "Test Description",
        }
        await client.post("/api/v1/documents/", files=files, data=data)

        # 一覧取得
        response = await client.get("/api/v1/documents/")
        assert response.status_code == 200
        result = response.json()

        # 文書フォーマットの検証
        doc = result["documents"][0]
        assert "document_id" in doc
        assert "title" in doc
        assert "file_name" in doc
        assert "file_size" in doc
        assert "content_type" in doc
        assert "category" in doc
        assert "tags" in doc
        assert isinstance(doc["tags"], list)
        assert "author" in doc
        assert "created_at" in doc
        assert "updated_at" in doc

        # ISO形式の日付文字列であることを確認
        assert datetime.fromisoformat(doc["created_at"])
        assert datetime.fromisoformat(doc["updated_at"])
