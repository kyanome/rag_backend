"""データベース接続管理。"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from ..config.settings import get_settings


class Base(DeclarativeBase):
    """SQLAlchemyのベースクラス。"""

    pass


# 設定の取得は遅延評価にする


class DatabaseManager:
    """データベース接続を管理するクラス。"""

    def __init__(self) -> None:
        """データベースマネージャーを初期化する。"""
        self._engine: AsyncEngine | None = None
        self._sessionmaker: async_sessionmaker[AsyncSession] | None = None
        self._settings = None

    @property
    def engine(self) -> AsyncEngine:
        """非同期エンジンを取得する。

        Returns:
            AsyncEngine: SQLAlchemy非同期エンジン
        """
        if self._engine is None:
            settings = get_settings()

            # SQLiteの場合は特殊な設定を使用
            if settings.database_url.startswith("sqlite"):
                self._engine = create_async_engine(
                    settings.database_url,
                    echo=settings.debug,
                    connect_args={"check_same_thread": False},
                )
            else:
                self._engine = create_async_engine(
                    settings.database_url,
                    echo=settings.debug,
                    pool_size=settings.database_pool_size,
                    max_overflow=settings.database_max_overflow,
                    pool_timeout=settings.database_pool_timeout,
                    pool_pre_ping=True,  # 接続の健全性チェック
                )
        return self._engine

    @property
    def sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        """非同期セッションメーカーを取得する。

        Returns:
            async_sessionmaker: 非同期セッションファクトリ
        """
        if self._sessionmaker is None:
            self._sessionmaker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )
        return self._sessionmaker

    async def close(self) -> None:
        """データベース接続を閉じる。"""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._sessionmaker = None

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """非同期セッションを取得するコンテキストマネージャー。

        Yields:
            AsyncSession: データベースセッション

        Example:
            async with db_manager.get_session() as session:
                # セッションを使用した処理
                pass
        """
        async with self.sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


# シングルトンインスタンス
db_manager = DatabaseManager()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPIの依存性注入用セッション取得関数。

    Yields:
        AsyncSession: データベースセッション
    """
    async with db_manager.get_session() as session:
        yield session


def async_session_factory() -> async_sessionmaker[AsyncSession]:
    """非同期セッションファクトリーを取得する。

    Returns:
        async_sessionmaker: セッションファクトリー
    """
    return db_manager.sessionmaker


async def init_database() -> None:
    """データベースを初期化する。"""
    # エンジンを取得（接続を確立）
    _ = db_manager.engine


async def create_all_tables() -> None:
    """すべてのテーブルを作成する。

    テスト用の関数。
    """
    from .models import Base as ModelBase

    async with db_manager.engine.begin() as conn:
        await conn.run_sync(ModelBase.metadata.create_all)
