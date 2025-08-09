"""プレーンテキスト抽出実装。

テキストファイルやMarkdownファイルからテキストを抽出する。
"""

import chardet

from ....domain.externals import ExtractedText, TextExtractor


class PlainTextExtractor(TextExtractor):
    """プレーンテキスト抽出実装。

    テキストファイル、Markdownファイル、CSVファイルなどの
    プレーンテキスト形式からテキストを抽出する。
    """

    SUPPORTED_TYPES = {
        "text/plain",
        "text/markdown",
        "text/csv",
        "text/x-markdown",
        "application/x-markdown",
    }

    async def extract_text(self, content: bytes, content_type: str) -> ExtractedText:
        """プレーンテキストからテキストを抽出する。

        Args:
            content: ファイルのバイナリデータ
            content_type: ファイルのMIMEタイプ

        Returns:
            抽出されたテキスト

        Raises:
            ValueError: サポートされていない形式の場合
            UnicodeDecodeError: 文字エンコーディングエラー
        """
        if not self.supports(content_type):
            raise ValueError(f"Unsupported content type: {content_type}")

        # 文字エンコーディングを検出
        detected = chardet.detect(content)
        encoding = detected.get("encoding", "utf-8") or "utf-8"
        confidence = detected.get("confidence", 0.0)

        # 信頼度が低い場合はUTF-8を試す
        if confidence < 0.7:
            encoding = "utf-8"

        try:
            text = content.decode(encoding)
        except UnicodeDecodeError:
            # UTF-8で再試行
            try:
                text = content.decode("utf-8", errors="ignore")
            except UnicodeDecodeError:
                # それでも失敗したらエラーを投げる
                raise UnicodeDecodeError(
                    encoding,
                    content,
                    0,
                    len(content),
                    f"Failed to decode text with encoding: {encoding}",
                ) from None

        # BOMを削除
        if text.startswith("\ufeff"):
            text = text[1:]

        metadata: dict[str, str | int | float] = {
            "encoding": encoding,
            "confidence": confidence,
            "line_count": text.count("\n") + 1,
            "char_count": len(text),
        }

        return ExtractedText(content=text, metadata=metadata)

    def supports(self, content_type: str) -> bool:
        """指定されたコンテンツタイプをサポートしているか判定する。

        Args:
            content_type: ファイルのMIMEタイプ

        Returns:
            サポートしている場合True
        """
        # MIMEタイプの基本部分のみを比較（charset部分を除外）
        base_type = content_type.split(";")[0].strip().lower()
        return base_type in self.SUPPORTED_TYPES
