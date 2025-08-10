"""インデックスパフォーマンス分析スクリプト。

PostgreSQLのインデックス使用状況とクエリプランを分析します。
"""

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.config.settings import Settings
from src.infrastructure.database.connection import db_manager


class IndexPerformanceAnalyzer:
    """インデックスパフォーマンス分析クラス。"""

    def __init__(self, session: AsyncSession) -> None:
        """初期化。

        Args:
            session: データベースセッション
        """
        self.session = session

    async def analyze_index_usage(self) -> dict[str, Any]:
        """インデックス使用状況を分析。

        Returns:
            インデックス使用状況のレポート
        """
        # PostgreSQL専用のクエリ
        index_usage_query = text(
            """
            SELECT 
                schemaname,
                tablename,
                indexname,
                idx_scan as index_scans,
                idx_tup_read as tuples_read,
                idx_tup_fetch as tuples_fetched,
                pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
                CASE 
                    WHEN idx_scan = 0 THEN 'UNUSED'
                    WHEN idx_scan < 100 THEN 'RARELY_USED'
                    WHEN idx_scan < 1000 THEN 'OCCASIONALLY_USED'
                    ELSE 'FREQUENTLY_USED'
                END as usage_category
            FROM pg_stat_user_indexes
            WHERE schemaname = 'public'
            ORDER BY idx_scan DESC;
        """
        )

        result = await self.session.execute(index_usage_query)
        rows = result.fetchall()

        return {
            "index_usage": [
                {
                    "table": row.tablename,
                    "index": row.indexname,
                    "scans": row.index_scans,
                    "tuples_read": row.tuples_read,
                    "tuples_fetched": row.tuples_fetched,
                    "size": row.index_size,
                    "usage": row.usage_category,
                }
                for row in rows
            ]
        }

    async def analyze_query_plans(self) -> dict[str, Any]:
        """主要なクエリのプランを分析。

        Returns:
            クエリプランのレポート
        """
        queries_to_analyze = [
            # ベクトル検索クエリ
            {
                "name": "vector_search",
                "query": """
                    EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
                    SELECT id, document_id, content, 
                           embedding <=> '[0.1, 0.2, 0.3]'::vector as distance
                    FROM document_chunks
                    ORDER BY embedding <=> '[0.1, 0.2, 0.3]'::vector
                    LIMIT 10;
                """,
            },
            # キーワード検索クエリ
            {
                "name": "keyword_search",
                "query": """
                    EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
                    SELECT id, document_id, content
                    FROM document_chunks
                    WHERE to_tsvector('english', content) @@ plainto_tsquery('test query')
                    LIMIT 10;
                """,
            },
            # メタデータフィルタクエリ
            {
                "name": "metadata_filter",
                "query": """
                    EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
                    SELECT d.id, d.title
                    FROM documents d
                    WHERE d.document_metadata @> '{"category": "技術文書"}'::jsonb
                    LIMIT 10;
                """,
            },
        ]

        plans = {}
        for query_info in queries_to_analyze:
            try:
                result = await self.session.execute(text(query_info["query"]))
                plan_data = result.scalar()
                plans[query_info["name"]] = self._parse_query_plan(plan_data)
            except Exception as e:
                plans[query_info["name"]] = {"error": str(e)}

        return {"query_plans": plans}

    def _parse_query_plan(self, plan_json: str) -> dict[str, Any]:
        """クエリプランを解析。

        Args:
            plan_json: JSON形式のクエリプラン

        Returns:
            解析されたプラン情報
        """
        plan = json.loads(plan_json)[0]

        return {
            "execution_time": plan.get("Execution Time", 0),
            "planning_time": plan.get("Planning Time", 0),
            "total_time": plan.get("Execution Time", 0) + plan.get("Planning Time", 0),
            "uses_index": self._check_index_usage(plan["Plan"]),
            "node_type": plan["Plan"]["Node Type"],
            "rows": plan["Plan"].get("Actual Rows", 0),
        }

    def _check_index_usage(self, plan_node: dict[str, Any]) -> bool:
        """プランノードでインデックスが使用されているか確認。

        Args:
            plan_node: プランノード

        Returns:
            インデックスが使用されているか
        """
        index_scan_types = {
            "Index Scan",
            "Index Only Scan",
            "Bitmap Index Scan",
            "Index Scan Backward",
        }

        if plan_node.get("Node Type") in index_scan_types:
            return True

        # 子ノードを再帰的にチェック
        if "Plans" in plan_node:
            for child in plan_node["Plans"]:
                if self._check_index_usage(child):
                    return True

        return False

    async def analyze_table_statistics(self) -> dict[str, Any]:
        """テーブル統計情報を分析。

        Returns:
            テーブル統計のレポート
        """
        stats_query = text(
            """
            SELECT 
                schemaname,
                tablename,
                n_live_tup as live_tuples,
                n_dead_tup as dead_tuples,
                last_vacuum,
                last_autovacuum,
                last_analyze,
                last_autoanalyze,
                vacuum_count,
                autovacuum_count,
                analyze_count,
                autoanalyze_count
            FROM pg_stat_user_tables
            WHERE schemaname = 'public'
            ORDER BY n_live_tup DESC;
        """
        )

        result = await self.session.execute(stats_query)
        rows = result.fetchall()

        return {
            "table_statistics": [
                {
                    "table": row.tablename,
                    "live_tuples": row.live_tuples,
                    "dead_tuples": row.dead_tuples,
                    "dead_tuple_ratio": (
                        row.dead_tuples / (row.live_tuples + row.dead_tuples)
                        if row.live_tuples + row.dead_tuples > 0
                        else 0
                    ),
                    "last_vacuum": (
                        row.last_vacuum.isoformat() if row.last_vacuum else None
                    ),
                    "last_analyze": (
                        row.last_analyze.isoformat() if row.last_analyze else None
                    ),
                    "vacuum_count": row.vacuum_count,
                    "analyze_count": row.analyze_count,
                }
                for row in rows
            ]
        }

    async def generate_recommendations(self, analysis: dict[str, Any]) -> list[str]:
        """分析結果に基づく推奨事項を生成。

        Args:
            analysis: 分析結果

        Returns:
            推奨事項のリスト
        """
        recommendations = []

        # 未使用インデックスの確認
        if "index_usage" in analysis:
            unused_indexes = [
                idx for idx in analysis["index_usage"] if idx["usage"] == "UNUSED"
            ]
            if unused_indexes:
                recommendations.append(
                    f"未使用のインデックスが{len(unused_indexes)}個見つかりました。"
                    "削除を検討してください。"
                )

        # デッドタプルの確認
        if "table_statistics" in analysis:
            high_dead_tuple_tables = [
                tbl
                for tbl in analysis["table_statistics"]
                if tbl["dead_tuple_ratio"] > 0.2
            ]
            if high_dead_tuple_tables:
                recommendations.append(
                    f"デッドタプル比率が高いテーブルが{len(high_dead_tuple_tables)}個"
                    "見つかりました。VACUUMの実行を検討してください。"
                )

        # クエリプランの確認
        if "query_plans" in analysis:
            slow_queries = [
                name
                for name, plan in analysis["query_plans"].items()
                if isinstance(plan, dict) and plan.get("total_time", 0) > 100
            ]
            if slow_queries:
                recommendations.append(
                    f"実行時間が100ms以上のクエリが{len(slow_queries)}個"
                    "見つかりました。最適化を検討してください。"
                )

        return recommendations


async def main() -> None:
    """メイン実行関数。"""
    settings = Settings()

    # PostgreSQL接続の場合のみ実行
    if "postgresql" not in settings.database_url:
        print("このスクリプトはPostgreSQLでのみ動作します。")
        return

    print("インデックスパフォーマンス分析を開始します...")
    print("=" * 60)

    async with db_manager.session() as session:
        analyzer = IndexPerformanceAnalyzer(session)

        # 各種分析を実行
        print("\n1. インデックス使用状況の分析...")
        index_usage = await analyzer.analyze_index_usage()

        print("\n2. クエリプランの分析...")
        query_plans = await analyzer.analyze_query_plans()

        print("\n3. テーブル統計の分析...")
        table_stats = await analyzer.analyze_table_statistics()

        # 結果を統合
        analysis_report = {
            **index_usage,
            **query_plans,
            **table_stats,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # 推奨事項を生成
        recommendations = await analyzer.generate_recommendations(analysis_report)
        analysis_report["recommendations"] = recommendations

        # レポートを出力
        print("\n" + "=" * 60)
        print("分析レポート")
        print("=" * 60)

        # インデックス使用状況
        print("\n■ インデックス使用状況:")
        for idx in analysis_report.get("index_usage", [])[:10]:
            print(f"  - {idx['index']}: {idx['scans']}スキャン ({idx['usage']})")

        # クエリプラン
        print("\n■ クエリパフォーマンス:")
        for name, plan in analysis_report.get("query_plans", {}).items():
            if isinstance(plan, dict) and "error" not in plan:
                print(
                    f"  - {name}: {plan.get('total_time', 0):.2f}ms "
                    f"(インデックス使用: {plan.get('uses_index', False)})"
                )

        # テーブル統計
        print("\n■ テーブル統計:")
        for tbl in analysis_report.get("table_statistics", [])[:5]:
            print(
                f"  - {tbl['table']}: {tbl['live_tuples']}行 "
                f"(デッドタプル率: {tbl['dead_tuple_ratio']:.1%})"
            )

        # 推奨事項
        print("\n■ 推奨事項:")
        for rec in recommendations:
            print(f"  • {rec}")

        # JSONファイルに保存
        output_file = (
            f"index_analysis_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(analysis_report, f, indent=2, ensure_ascii=False, default=str)

        print(f"\n詳細レポートを{output_file}に保存しました。")


if __name__ == "__main__":
    asyncio.run(main())
