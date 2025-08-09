"""ベクトルストレージ関連の例外定義。

DDDの原則に従い、ドメイン層で例外を定義。
"""


class VectorStorageError(Exception):
    """ベクトルストレージに関する基底例外クラス。"""

    pass


class VectorStorageConnectionError(VectorStorageError):
    """ベクトルストレージへの接続エラー。"""

    pass


class VectorStorageSaveError(VectorStorageError):
    """ベクトルの保存時エラー。"""

    pass


class VectorStorageSearchError(VectorStorageError):
    """ベクトル検索時のエラー。"""

    pass


class VectorStorageTimeoutError(VectorStorageError):
    """ベクトル操作のタイムアウトエラー。"""

    pass


class VectorStorageBatchError(VectorStorageError):
    """バッチ処理時のエラー。

    部分的な成功を含む場合がある。
    """

    def __init__(
        self,
        message: str,
        successful_ids: list[str] | None = None,
        failed_ids: list[str] | None = None,
    ):
        """初期化する。

        Args:
            message: エラーメッセージ
            successful_ids: 成功したチャンクIDのリスト
            failed_ids: 失敗したチャンクIDのリスト
        """
        super().__init__(message)
        self.successful_ids = successful_ids or []
        self.failed_ids = failed_ids or []
