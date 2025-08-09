"""アプリケーション設定管理。"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """アプリケーション設定。

    環境変数から設定を読み込み、バリデーションを行う。
    """

    # Database Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/ragdb",
        description="PostgreSQL接続URL（非同期版）",
    )

    # File Storage Configuration
    file_storage_path: Path = Field(
        default=Path("./uploads"),
        description="ファイルストレージのベースパス",
    )

    # Application Configuration
    debug: bool = Field(default=False, description="デバッグモード")
    log_level: str = Field(default="INFO", description="ログレベル")

    # Azure Configuration (optional for now)
    azure_storage_connection_string: str | None = Field(
        default=None,
        description="Azure Blob Storage接続文字列",
    )
    azure_storage_container_name: str | None = Field(
        default=None,
        description="Azure Blob Storageコンテナ名",
    )

    # Database Pool Configuration
    database_pool_size: int = Field(
        default=10, description="データベース接続プールサイズ"
    )
    database_max_overflow: int = Field(
        default=20, description="最大オーバーフロー接続数"
    )
    database_pool_timeout: int = Field(default=30, description="接続タイムアウト（秒）")

    # JWT Configuration
    jwt_secret_key: str = Field(
        default="your-secret-key-here-change-in-production",
        description="JWT署名用の秘密鍵",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT署名アルゴリズム")
    access_token_expire_minutes: int = Field(
        default=15, description="アクセストークン有効期限（分）"
    )
    refresh_token_expire_days: int = Field(
        default=30, description="リフレッシュトークン有効期限（日）"
    )

    # CORS Configuration
    cors_allowed_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001"],
        description="許可されたCORSオリジンのリスト",
    )
    cors_allow_credentials: bool = Field(
        default=True,
        description="CORSでクレデンシャル（Cookie、認証ヘッダー）を許可",
    )
    cors_allow_methods: list[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="許可されたHTTPメソッド",
    )
    cors_allow_headers: list[str] = Field(
        default=["*"],
        description="許可されたHTTPヘッダー",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("file_storage_path", mode="before")
    @classmethod
    def validate_file_storage_path(cls, v: str | Path) -> Path:
        """ファイルストレージパスのバリデーション。"""
        path = Path(v) if isinstance(v, str) else v
        return path.absolute()

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """ログレベルのバリデーション。"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v_upper

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_key(cls, v: str) -> str:
        """JWT秘密鍵のバリデーション。"""
        if v == "your-secret-key-here-change-in-production":
            import warnings

            warnings.warn(
                "Using default JWT secret key. Please set JWT_SECRET_KEY in production!",
                UserWarning,
                stacklevel=2,
            )
        elif len(v) < 32:
            raise ValueError("JWT secret key must be at least 32 characters long")
        return v

    @field_validator("cors_allowed_origins")
    @classmethod
    def validate_cors_origins(cls, v: list[str]) -> list[str]:
        """CORSオリジンのバリデーション。"""
        if "*" in v and len(v) > 1:
            raise ValueError(
                "CORS: Cannot use wildcard '*' with other specific origins"
            )
        # Production環境では具体的なオリジンを指定すべき
        if "*" in v:
            import warnings

            warnings.warn(
                "Using wildcard '*' for CORS origins. This is insecure in production!",
                UserWarning,
                stacklevel=2,
            )
        return v

    def ensure_file_storage_path(self) -> None:
        """ファイルストレージディレクトリを作成する。"""
        self.file_storage_path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """設定のシングルトンインスタンスを取得する。

    Returns:
        Settings: アプリケーション設定
    """
    return Settings()
