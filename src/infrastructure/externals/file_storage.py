"""ローカルファイルストレージサービス。"""

import hashlib
from pathlib import Path

import anyio
from anyio import Path as AsyncPath

from ..config.settings import get_settings


class FileStorageService:
    """ローカルファイルシステムへのファイル保存・読み込みを管理する。

    将来的にAzure Blob Storageへの切り替えを考慮した設計。
    """

    def __init__(self, base_path: Path | None = None) -> None:
        """ファイルストレージサービスを初期化する。

        Args:
            base_path: ファイル保存のベースパス。指定しない場合は設定から取得。
        """
        settings = get_settings()
        self.base_path = base_path or settings.file_storage_path
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, document_id: str, file_name: str) -> Path:
        """ファイルの保存パスを生成する。

        Args:
            document_id: 文書ID
            file_name: オリジナルファイル名

        Returns:
            Path: ファイルの保存パス
        """
        # セキュリティのため、document_idベースのディレクトリ構造を使用
        # 例: uploads/ab/cd/abcd-1234-5678-9012/original_filename.pdf
        id_hash = hashlib.sha256(document_id.encode()).hexdigest()
        dir_path = self.base_path / id_hash[:2] / id_hash[2:4] / document_id
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path / file_name

    async def save(self, document_id: str, file_name: str, content: bytes) -> str:
        """ファイルを保存する。

        Args:
            document_id: 文書ID
            file_name: ファイル名
            content: ファイルの内容

        Returns:
            str: 保存されたファイルのパス（相対パス）

        Raises:
            IOError: ファイル保存に失敗した場合
        """
        try:
            file_path = self._get_file_path(document_id, file_name)
            async_path = AsyncPath(file_path)
            await async_path.write_bytes(content)

            # ベースパスからの相対パスを返す
            return str(file_path.relative_to(self.base_path))
        except Exception as e:
            raise OSError(f"Failed to save file: {e}") from e

    async def load(self, relative_path: str) -> bytes:
        """ファイルを読み込む。

        Args:
            relative_path: ファイルの相対パス

        Returns:
            bytes: ファイルの内容

        Raises:
            FileNotFoundError: ファイルが存在しない場合
            IOError: ファイル読み込みに失敗した場合
        """
        try:
            file_path = self.base_path / relative_path
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {relative_path}")

            async_path = AsyncPath(file_path)
            return await async_path.read_bytes()
        except FileNotFoundError:
            raise
        except Exception as e:
            raise OSError(f"Failed to load file: {e}") from e

    async def delete(self, relative_path: str) -> None:
        """ファイルを削除する。

        Args:
            relative_path: ファイルの相対パス

        Raises:
            FileNotFoundError: ファイルが存在しない場合
            IOError: ファイル削除に失敗した場合
        """
        try:
            file_path = self.base_path / relative_path
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {relative_path}")

            async_path = AsyncPath(file_path)
            await async_path.unlink()

            # 空のディレクトリを削除（親ディレクトリも含めて）
            parent = file_path.parent
            while parent != self.base_path and parent.exists():
                try:
                    if not any(parent.iterdir()):
                        parent.rmdir()
                        parent = parent.parent
                    else:
                        break
                except OSError:
                    break
        except FileNotFoundError:
            raise
        except Exception as e:
            raise OSError(f"Failed to delete file: {e}") from e

    async def exists(self, relative_path: str) -> bool:
        """ファイルが存在するかチェックする。

        Args:
            relative_path: ファイルの相対パス

        Returns:
            bool: ファイルが存在する場合True
        """
        file_path = self.base_path / relative_path
        return await anyio.to_thread.run_sync(file_path.exists)

    async def get_size(self, relative_path: str) -> int:
        """ファイルサイズを取得する。

        Args:
            relative_path: ファイルの相対パス

        Returns:
            int: ファイルサイズ（バイト）

        Raises:
            FileNotFoundError: ファイルが存在しない場合
        """
        file_path = self.base_path / relative_path
        if not await self.exists(relative_path):
            raise FileNotFoundError(f"File not found: {relative_path}")

        stat = await anyio.to_thread.run_sync(file_path.stat)
        return stat.st_size
