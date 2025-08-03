#!/usr/bin/env python
"""データベース初期化スクリプト"""

import asyncio
import sys
from pathlib import Path

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.infrastructure.database.connection import create_all_tables, db_manager


async def main():
    """データベースを初期化する"""
    print("データベースの初期化を開始します...")
    
    try:
        # テーブルを作成
        await create_all_tables()
        print("✅ テーブルの作成が完了しました")
        
        # 接続を閉じる
        await db_manager.close()
        print("✅ データベースの初期化が完了しました")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())