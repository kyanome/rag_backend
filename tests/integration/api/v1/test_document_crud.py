"""文書CRUD APIの統合テスト。"""

import tempfile
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from pathlib import Path

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import Document
from src.domain.value_objects import DocumentId, DocumentMetadata
from src.infrastructure.config.settings import Settings
from src.infrastructure.database.connection import create_all_tables, db_manager
from src.infrastructure.database.models import DocumentModel
from src.infrastructure.externals import FileStorageService
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


@pytest.fixture
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    """テスト用のデータベースセッション。"""
    # db_manager経由でセッションを取得
    async with db_manager.get_session() as session:
        yield session


@pytest.fixture
async def sample_document_in_db(
    async_session: AsyncSession,
    test_settings: Settings,
) -> Document:
    """データベースにサンプル文書を作成する。"""
    # ドメインエンティティを作成
    metadata = DocumentMetadata(
        file_name="test.pdf",
        file_size=1024,
        content_type="application/pdf",
        category="技術文書",
        tags=["テスト", "サンプル"],
        author="テストユーザー",
        description="テスト用の文書です",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    document = Document.create(
        title="テスト文書",
        content=b"test content",
        metadata=metadata,
        document_id=DocumentId(value=str(uuid.uuid4())),
    )

    # ファイルを保存
    file_storage = FileStorageService(base_path=test_settings.file_storage_path)
    file_path = await file_storage.save(
        document_id=document.id.value,
        file_name=document.metadata.file_name,
        content=document.content,
    )

    # データベースモデルを作成
    model = DocumentModel.from_domain(document)
    model.file_path = file_path  # type: ignore[assignment]

    async_session.add(model)
    await async_session.commit()

    return document


class TestDocumentDetailAPI:
    """文書詳細取得APIのテスト。"""

    @pytest.mark.anyio
    async def test_get_document_success(
        self,
        client: AsyncClient,
        sample_document_in_db: Document,
    ) -> None:
        """文書詳細を正常に取得できることを確認する。"""
        # Act
        response = await client.get(
            f"/api/v1/documents/{sample_document_in_db.id.value}"
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["document_id"] == sample_document_in_db.id.value
        assert data["title"] == "テスト文書"
        assert data["file_name"] == "test.pdf"
        assert data["file_size"] == 1024
        assert data["content_type"] == "application/pdf"
        assert data["category"] == "技術文書"
        assert data["tags"] == ["テスト", "サンプル"]
        assert data["author"] == "テストユーザー"
        assert data["description"] == "テスト用の文書です"
        assert data["version"] == 1

    @pytest.mark.anyio
    async def test_get_document_not_found(
        self,
        client: AsyncClient,
    ) -> None:
        """存在しない文書の取得で404エラーが返ることを確認する。"""
        # Act
        non_existent_id = str(uuid.uuid4())
        response = await client.get(f"/api/v1/documents/{non_existent_id}")

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert f"Document with id '{non_existent_id}' not found" in data["detail"]


class TestDocumentUpdateAPI:
    """文書更新APIのテスト。"""

    @pytest.mark.anyio
    async def test_update_document_success(
        self,
        client: AsyncClient,
        sample_document_in_db: Document,
    ) -> None:
        """文書を正常に更新できることを確認する。"""
        # Arrange
        update_data = {
            "title": "更新されたタイトル",
            "category": "更新カテゴリ",
            "tags": ["新タグ1", "新タグ2"],
            "author": "更新ユーザー",
            "description": "更新された説明",
        }

        # Act
        response = await client.put(
            f"/api/v1/documents/{sample_document_in_db.id.value}",
            json=update_data,
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["document_id"] == sample_document_in_db.id.value
        assert data["title"] == "更新されたタイトル"
        assert data["category"] == "更新カテゴリ"
        assert data["tags"] == ["新タグ1", "新タグ2"]
        assert data["author"] == "更新ユーザー"
        assert data["description"] == "更新された説明"
        assert data["version"] == 2  # バージョンが増加

    @pytest.mark.anyio
    async def test_update_document_partial(
        self,
        client: AsyncClient,
        sample_document_in_db: Document,
    ) -> None:
        """文書の一部フィールドのみ更新できることを確認する。"""
        # Arrange
        update_data = {
            "title": "部分更新タイトル",
        }

        # Act
        response = await client.put(
            f"/api/v1/documents/{sample_document_in_db.id.value}",
            json=update_data,
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == "部分更新タイトル"
        # 他のフィールドは変更されていない
        assert data["category"] == "技術文書"
        assert data["tags"] == ["テスト", "サンプル"]

    @pytest.mark.anyio
    async def test_update_document_not_found(
        self,
        client: AsyncClient,
    ) -> None:
        """存在しない文書の更新で404エラーが返ることを確認する。"""
        # Arrange
        non_existent_id = str(uuid.uuid4())
        update_data = {"title": "新しいタイトル"}

        # Act
        response = await client.put(
            f"/api/v1/documents/{non_existent_id}",
            json=update_data,
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert f"Document with id '{non_existent_id}' not found" in data["detail"]

    @pytest.mark.anyio
    async def test_update_document_no_fields(
        self,
        client: AsyncClient,
        sample_document_in_db: Document,
    ) -> None:
        """更新フィールドが指定されていない場合に400エラーが返ることを確認する。"""
        # Arrange
        update_data = {}

        # Act
        response = await client.put(
            f"/api/v1/documents/{sample_document_in_db.id.value}",
            json=update_data,
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "At least one field must be provided for update" in data["detail"]

    @pytest.mark.anyio
    async def test_update_document_invalid_title(
        self,
        client: AsyncClient,
        sample_document_in_db: Document,
    ) -> None:
        """無効なタイトルの更新で400エラーが返ることを確認する。"""
        # Arrange
        update_data = {"title": "   "}  # 空白のみ

        # Act
        response = await client.put(
            f"/api/v1/documents/{sample_document_in_db.id.value}",
            json=update_data,
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Title cannot be empty" in data["detail"]


class TestDocumentDeleteAPI:
    """文書削除APIのテスト。"""

    @pytest.mark.anyio
    async def test_delete_document_success(
        self,
        client: AsyncClient,
        sample_document_in_db: Document,
        test_settings: Settings,
    ) -> None:
        """文書を正常に削除できることを確認する。"""
        # Act
        response = await client.delete(
            f"/api/v1/documents/{sample_document_in_db.id.value}"
        )

        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # 文書が削除されていることを確認
        get_response = await client.get(
            f"/api/v1/documents/{sample_document_in_db.id.value}"
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

        # ファイルも削除されていることを確認
        file_path = (
            test_settings.file_storage_path
            / sample_document_in_db.id.value
            / sample_document_in_db.metadata.file_name
        )
        assert not file_path.exists()

    @pytest.mark.anyio
    async def test_delete_document_not_found(
        self,
        client: AsyncClient,
    ) -> None:
        """存在しない文書の削除で404エラーが返ることを確認する。"""
        # Act
        non_existent_id = str(uuid.uuid4())
        response = await client.delete(f"/api/v1/documents/{non_existent_id}")

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert f"Document with id '{non_existent_id}' not found" in data["detail"]

    @pytest.mark.anyio
    async def test_delete_document_twice(
        self,
        client: AsyncClient,
        sample_document_in_db: Document,
    ) -> None:
        """同じ文書を2回削除しようとすると2回目は404エラーが返ることを確認する。"""
        # Act - 1回目の削除
        response1 = await client.delete(
            f"/api/v1/documents/{sample_document_in_db.id.value}"
        )
        assert response1.status_code == status.HTTP_204_NO_CONTENT

        # Act - 2回目の削除
        response2 = await client.delete(
            f"/api/v1/documents/{sample_document_in_db.id.value}"
        )

        # Assert
        assert response2.status_code == status.HTTP_404_NOT_FOUND


class TestDocumentCRUDFlow:
    """文書のCRUD操作の統合フローテスト。"""

    @pytest.mark.anyio
    async def test_full_crud_flow(
        self,
        client: AsyncClient,
        tmp_path: Path,
    ) -> None:
        """文書の作成・取得・更新・削除の一連のフローをテストする。"""
        # 1. Create - 文書をアップロード
        with open(tmp_path / "test.pdf", "wb") as f:
            f.write(b"test content for crud flow")

        with open(tmp_path / "test.pdf", "rb") as f:
            response = await client.post(
                "/api/v1/documents/",
                files={"file": ("test.pdf", f, "application/pdf")},
                data={
                    "title": "CRUD テスト文書",
                    "category": "テスト",
                    "tags": "tag1,tag2",
                    "author": "テストユーザー",
                    "description": "CRUD フローテスト用",
                },
            )

        assert response.status_code == status.HTTP_201_CREATED
        document_id = response.json()["document_id"]

        # 2. Read - 作成した文書を取得
        response = await client.get(f"/api/v1/documents/{document_id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == "CRUD テスト文書"
        assert data["version"] == 1

        # 3. Update - 文書を更新
        update_data = {
            "title": "更新された CRUD テスト文書",
            "tags": ["更新タグ1", "更新タグ2", "更新タグ3"],
        }
        response = await client.put(
            f"/api/v1/documents/{document_id}",
            json=update_data,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == "更新された CRUD テスト文書"
        assert data["tags"] == ["更新タグ1", "更新タグ2", "更新タグ3"]
        assert data["version"] == 2

        # 4. Delete - 文書を削除
        response = await client.delete(f"/api/v1/documents/{document_id}")
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # 5. Verify deletion - 削除されていることを確認
        response = await client.get(f"/api/v1/documents/{document_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
