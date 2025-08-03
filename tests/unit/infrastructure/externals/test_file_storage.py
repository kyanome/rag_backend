"""ファイルストレージサービスのテスト。"""

import uuid
from pathlib import Path

import pytest
from anyio import Path as AsyncPath

from src.infrastructure.externals.file_storage import FileStorageService


@pytest.fixture
async def file_storage(tmp_path: Path) -> FileStorageService:
    """テスト用のファイルストレージサービスを作成する。"""
    return FileStorageService(base_path=tmp_path)


@pytest.fixture
def document_id() -> str:
    """テスト用の文書IDを生成する。"""
    return str(uuid.uuid4())


class TestFileStorageService:
    """FileStorageServiceのテストクラス。"""

    async def test_save_and_load(
        self, file_storage: FileStorageService, document_id: str
    ) -> None:
        """ファイルの保存と読み込みをテストする。"""
        file_name = "test.pdf"
        content = b"Test content for PDF file"

        relative_path = await file_storage.save(document_id, file_name, content)

        assert relative_path is not None
        assert file_name in relative_path

        loaded_content = await file_storage.load(relative_path)
        assert loaded_content == content

    async def test_save_creates_directory_structure(
        self, file_storage: FileStorageService, document_id: str
    ) -> None:
        """ディレクトリ構造の作成をテストする。"""
        file_name = "test.txt"
        content = b"Test content"

        relative_path = await file_storage.save(document_id, file_name, content)

        file_path = file_storage.base_path / relative_path
        assert file_path.exists()
        assert file_path.is_file()

        parts = Path(relative_path).parts
        assert len(parts) >= 4
        assert parts[-1] == file_name
        assert parts[-2] == document_id

    async def test_delete(
        self, file_storage: FileStorageService, document_id: str
    ) -> None:
        """ファイルの削除をテストする。"""
        file_name = "test_delete.pdf"
        content = b"Content to delete"

        relative_path = await file_storage.save(document_id, file_name, content)

        assert await file_storage.exists(relative_path)

        await file_storage.delete(relative_path)

        assert not await file_storage.exists(relative_path)

    async def test_delete_nonexistent_file(
        self, file_storage: FileStorageService
    ) -> None:
        """存在しないファイルの削除をテストする。"""
        with pytest.raises(FileNotFoundError):
            await file_storage.delete("nonexistent/file.pdf")

    async def test_load_nonexistent_file(
        self, file_storage: FileStorageService
    ) -> None:
        """存在しないファイルの読み込みをテストする。"""
        with pytest.raises(FileNotFoundError):
            await file_storage.load("nonexistent/file.pdf")

    async def test_exists(
        self, file_storage: FileStorageService, document_id: str
    ) -> None:
        """ファイルの存在確認をテストする。"""
        file_name = "test_exists.txt"
        content = b"Test content"

        relative_path = await file_storage.save(document_id, file_name, content)

        assert await file_storage.exists(relative_path)
        assert not await file_storage.exists("nonexistent/file.txt")

    async def test_get_size(
        self, file_storage: FileStorageService, document_id: str
    ) -> None:
        """ファイルサイズの取得をテストする。"""
        file_name = "test_size.txt"
        content = b"Test content with known size"

        relative_path = await file_storage.save(document_id, file_name, content)

        size = await file_storage.get_size(relative_path)
        assert size == len(content)

    async def test_get_size_nonexistent_file(
        self, file_storage: FileStorageService
    ) -> None:
        """存在しないファイルのサイズ取得をテストする。"""
        with pytest.raises(FileNotFoundError):
            await file_storage.get_size("nonexistent/file.txt")

    async def test_save_with_unicode_filename(
        self, file_storage: FileStorageService, document_id: str
    ) -> None:
        """Unicode文字を含むファイル名での保存をテストする。"""
        file_name = "テスト文書.pdf"
        content = b"Japanese filename test"

        relative_path = await file_storage.save(document_id, file_name, content)

        assert file_name in relative_path

        loaded_content = await file_storage.load(relative_path)
        assert loaded_content == content

    async def test_save_empty_file(
        self, file_storage: FileStorageService, document_id: str
    ) -> None:
        """空ファイルの保存をテストする。"""
        file_name = "empty.txt"
        content = b""

        relative_path = await file_storage.save(document_id, file_name, content)

        loaded_content = await file_storage.load(relative_path)
        assert loaded_content == content
        assert len(loaded_content) == 0

    async def test_delete_cleans_empty_directories(
        self, file_storage: FileStorageService, document_id: str
    ) -> None:
        """ファイル削除時の空ディレクトリ削除をテストする。"""
        file_name = "test_cleanup.txt"
        content = b"Test content"

        relative_path = await file_storage.save(document_id, file_name, content)
        file_path = file_storage.base_path / relative_path
        parent_dir = file_path.parent

        await file_storage.delete(relative_path)

        assert not parent_dir.exists()

    async def test_save_io_error(
        self, file_storage: FileStorageService, document_id: str, monkeypatch
    ) -> None:
        """保存時のIOエラーをテストする。"""

        async def mock_write_bytes(self, content):
            raise OSError("Mock IO error")

        monkeypatch.setattr(AsyncPath, "write_bytes", mock_write_bytes)

        with pytest.raises(IOError, match="Failed to save file"):
            await file_storage.save(document_id, "test.txt", b"content")
