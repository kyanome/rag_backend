"""pytest共通設定。"""

import os
import pytest

# テスト実行時にSQLiteを使用するように環境変数を設定
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["TESTING"] = "1"

@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """anyioのバックエンドを指定。"""
    return "asyncio"