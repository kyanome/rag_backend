"""PDF テキスト抽出実装。

PDFファイルからテキストを抽出する。
"""

import io
from typing import Any

from pypdf import PdfReader

from ....domain.externals import ExtractedText, TextExtractor


class PyPDFTextExtractor(TextExtractor):
    """PDF テキスト抽出実装。

    pypdfライブラリを使用してPDFファイルからテキストを抽出する。
    """

    SUPPORTED_TYPES = {"application/pdf", "application/x-pdf"}

    async def extract_text(
        self, content: bytes, content_type: str
    ) -> ExtractedText:
        """PDFからテキストを抽出する。

        Args:
            content: PDFファイルのバイナリデータ
            content_type: ファイルのMIMEタイプ

        Returns:
            抽出されたテキスト

        Raises:
            ValueError: サポートされていない形式の場合
            Exception: PDF処理でエラーが発生した場合
        """
        if not self.supports(content_type):
            raise ValueError(f"Unsupported content type: {content_type}")

        try:
            # バイトストリームからPDFを読み込み
            pdf_file = io.BytesIO(content)
            reader = PdfReader(pdf_file)

            # 全ページからテキストを抽出
            text_parts = []
            page_count = len(reader.pages)

            for page_num, page in enumerate(reader.pages, start=1):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        # ページ区切りを追加
                        if text_parts:
                            text_parts.append("\n\n")
                        text_parts.append(page_text)
                except Exception as e:
                    # 特定のページで失敗しても続行
                    print(f"Failed to extract text from page {page_num}: {e}")
                    continue

            extracted_text = "".join(text_parts)

            # メタデータを収集
            metadata: dict[str, Any] = {
                "page_count": page_count,
                "char_count": len(extracted_text),
            }

            # PDFメタデータがあれば追加
            if reader.metadata:
                if hasattr(reader.metadata, "title") and reader.metadata.title:
                    metadata["title"] = str(reader.metadata.title)
                if hasattr(reader.metadata, "author") and reader.metadata.author:
                    metadata["author"] = str(reader.metadata.author)
                if (
                    hasattr(reader.metadata, "creation_date")
                    and reader.metadata.creation_date
                ):
                    metadata["creation_date"] = str(reader.metadata.creation_date)

            return ExtractedText(content=extracted_text, metadata=metadata)

        except Exception as e:
            raise Exception(f"Failed to extract text from PDF: {str(e)}") from e

    def supports(self, content_type: str) -> bool:
        """指定されたコンテンツタイプをサポートしているか判定する。

        Args:
            content_type: ファイルのMIMEタイプ

        Returns:
            サポートしている場合True
        """
        base_type = content_type.split(";")[0].strip().lower()
        return base_type in self.SUPPORTED_TYPES