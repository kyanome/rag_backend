"""複合テキスト抽出実装。

動的にファイルタイプに応じた抽出器を選択する。
"""

from ....domain.externals import ExtractedText, TextExtractor
from .text_extractor_factory import TextExtractorFactory


class CompositeTextExtractor(TextExtractor):
    """複合テキスト抽出実装。

    TextExtractorFactoryを使用して、ファイルタイプに応じて
    動的に適切なテキスト抽出器を選択して使用する。
    """

    def __init__(self) -> None:
        """初期化する。"""
        self._factory = TextExtractorFactory()

    async def extract_text(self, content: bytes, content_type: str) -> ExtractedText:
        """文書からテキストを抽出する。

        Args:
            content: 文書のバイナリデータ
            content_type: 文書のMIMEタイプ

        Returns:
            抽出されたテキスト

        Raises:
            ValueError: サポートされていない形式の場合
            Exception: 抽出処理でエラーが発生した場合
        """
        extractor = self._factory.get_extractor(content_type)
        return await extractor.extract_text(content, content_type)

    def supports(self, content_type: str) -> bool:
        """指定されたコンテンツタイプをサポートしているか判定する。

        Args:
            content_type: 文書のMIMEタイプ

        Returns:
            サポートしている場合True
        """
        return self._factory.supports(content_type)
