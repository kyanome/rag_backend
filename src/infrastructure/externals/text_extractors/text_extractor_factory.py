"""テキスト抽出ファクトリー。

ファイルタイプに応じて適切なテキスト抽出実装を選択する。
"""

from ....domain.externals import TextExtractor
from .docx_text_extractor import DocxTextExtractor
from .plain_text_extractor import PlainTextExtractor
from .pypdf_text_extractor import PyPDFTextExtractor


class TextExtractorFactory:
    """テキスト抽出ファクトリー。

    ファイルのコンテンツタイプに基づいて、適切なTextExtractor実装を
    選択して返すファクトリークラス。
    """

    def __init__(self) -> None:
        """初期化する。"""
        self._extractors: list[TextExtractor] = [
            PlainTextExtractor(),
            PyPDFTextExtractor(),
            DocxTextExtractor(),
        ]

    def get_extractor(self, content_type: str) -> TextExtractor:
        """コンテンツタイプに対応するテキスト抽出実装を取得する。

        Args:
            content_type: ファイルのMIMEタイプ

        Returns:
            対応するTextExtractor実装

        Raises:
            ValueError: サポートされていないコンテンツタイプの場合
        """
        for extractor in self._extractors:
            if extractor.supports(content_type):
                return extractor

        supported_types = self.get_supported_types()
        raise ValueError(
            f"No extractor found for content type: {content_type}. "
            f"Supported types: {', '.join(supported_types)}"
        )

    def get_supported_types(self) -> set[str]:
        """サポートされている全てのコンテンツタイプを取得する。

        Returns:
            サポートされているMIMEタイプのセット
        """
        supported = set()
        for extractor in self._extractors:
            # 各抽出実装がサポートするタイプを収集
            if isinstance(extractor, PlainTextExtractor):
                supported.update(PlainTextExtractor.SUPPORTED_TYPES)
            elif isinstance(extractor, PyPDFTextExtractor):
                supported.update(PyPDFTextExtractor.SUPPORTED_TYPES)
            elif isinstance(extractor, DocxTextExtractor):
                supported.update(DocxTextExtractor.SUPPORTED_TYPES)
        return supported

    def supports(self, content_type: str) -> bool:
        """指定されたコンテンツタイプがサポートされているか判定する。

        Args:
            content_type: ファイルのMIMEタイプ

        Returns:
            サポートしている場合True
        """
        return any(extractor.supports(content_type) for extractor in self._extractors)
