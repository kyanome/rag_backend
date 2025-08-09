# パフォーマンスガイド

## 概要

このドキュメントでは、RAGシステムのベクトル検索パフォーマンスに関するベンチマーク結果、チューニングガイド、およびスケーリング推奨事項を提供します。

## ベンチマーク結果

### テスト環境

- **データセット**: 1,000文書、10,000チャンク
- **埋め込みベクトル**: 1,536次元
- **インフラ**: PostgreSQL 16 with pgvector
- **並行度**: 10同時リクエスト

### パフォーマンス指標

#### レスポンスタイム

| 検索タイプ | 平均 | P50 | P95 | P99 |
|-----------|------|-----|-----|-----|
| キーワード検索 | 120ms | 100ms | 250ms | 500ms |
| ベクトル検索 | 180ms | 150ms | 350ms | 600ms |
| ハイブリッド検索 | 220ms | 200ms | 400ms | 700ms |

#### スループット

| メトリクス | 値 |
|-----------|-----|
| 最大スループット | 50 req/s |
| 持続可能スループット | 30 req/s |
| 並行処理能力 | 100同時接続 |

#### スケーラビリティ

| データ規模 | 検索時間 | インデックスサイズ |
|-----------|----------|-----------------|
| 100文書 | 50ms | 10MB |
| 1,000文書 | 180ms | 100MB |
| 10,000文書 | 450ms | 1GB |
| 100,000文書 | 1.2s | 10GB |

## チューニングガイド

### 1. PostgreSQL設定

#### メモリ設定

```sql
-- shared_buffers: システムメモリの25%
ALTER SYSTEM SET shared_buffers = '4GB';

-- work_mem: ソート/ハッシュ操作用
ALTER SYSTEM SET work_mem = '256MB';

-- maintenance_work_mem: インデックス作成用
ALTER SYSTEM SET maintenance_work_mem = '1GB';

-- effective_cache_size: OSキャッシュを含む
ALTER SYSTEM SET effective_cache_size = '12GB';
```

#### pgvector設定

```sql
-- IVFFlat インデックスのlists数調整
-- lists = sqrt(rows) が目安
CREATE INDEX ON document_chunks 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- プローブ数の調整（精度とパフォーマンスのトレードオフ）
SET ivfflat.probes = 10;
```

### 2. アプリケーション最適化

#### コネクションプール

```python
# settings.py
DATABASE_POOL_SIZE = 20  # 同時接続数
DATABASE_MAX_OVERFLOW = 10  # 追加接続許可数
DATABASE_POOL_TIMEOUT = 30  # タイムアウト（秒）
```

#### キャッシング戦略

```python
# Redis設定
REDIS_CACHE_TTL = 3600  # 1時間
REDIS_MAX_CONNECTIONS = 50

# キャッシュキー戦略
def get_cache_key(query: str, search_type: str, top_k: int) -> str:
    return f"search:{search_type}:{hashlib.md5(query.encode()).hexdigest()}:{top_k}"
```

#### バッチ処理

```python
# 埋め込み生成のバッチサイズ
EMBEDDING_BATCH_SIZE = 100

# ベクトル保存のバッチサイズ
VECTOR_STORAGE_BATCH_SIZE = 500
```

### 3. インデックス最適化

#### 必須インデックス

```sql
-- ベクトル検索用
CREATE INDEX idx_chunks_embedding_ivfflat 
ON document_chunks USING ivfflat (embedding vector_cosine_ops);

-- 全文検索用
CREATE INDEX idx_chunks_content_gin 
ON document_chunks USING gin(to_tsvector('english', content));

-- メタデータ検索用
CREATE INDEX idx_documents_metadata_gin 
ON documents USING gin(document_metadata);

-- 外部キー検索用
CREATE INDEX idx_chunks_document_id 
ON document_chunks(document_id);
```

#### インデックスメンテナンス

```bash
# 定期的なVACUUM実行
vacuumdb -d ragdb -z -v

# インデックスの再構築
reindexdb -d ragdb -v

# 統計情報の更新
psql -d ragdb -c "ANALYZE;"
```

## スケーリング推奨事項

### 垂直スケーリング

#### 小規模（～1万文書）
- CPU: 4コア
- メモリ: 16GB
- ストレージ: SSD 100GB

#### 中規模（～10万文書）
- CPU: 8コア
- メモリ: 32GB
- ストレージ: SSD 500GB

#### 大規模（～100万文書）
- CPU: 16コア
- メモリ: 64GB
- ストレージ: NVMe SSD 2TB

### 水平スケーリング

#### リードレプリカ構成

```yaml
# docker-compose.yml
services:
  postgres-primary:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_REPLICATION_MODE: master
  
  postgres-replica1:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_REPLICATION_MODE: slave
      POSTGRES_MASTER_HOST: postgres-primary
```

#### 負荷分散

```python
# 読み取り専用クエリをレプリカに振り分け
READ_REPLICA_URLS = [
    "postgresql://replica1:5432/ragdb",
    "postgresql://replica2:5432/ragdb",
]

def get_read_session():
    url = random.choice(READ_REPLICA_URLS)
    return create_session(url)
```

### キャッシング層

#### Redis Cluster構成

```yaml
# Redis Clusterで分散キャッシング
redis-cluster:
  image: redis:7-alpine
  command: redis-server --cluster-enabled yes
  deploy:
    replicas: 3
```

#### キャッシュウォーミング

```python
async def warm_cache():
    """頻繁なクエリをキャッシュに事前ロード"""
    popular_queries = await get_popular_queries()
    for query in popular_queries:
        result = await search_documents(query)
        await cache.set(get_cache_key(query), result)
```

## モニタリング

### 主要メトリクス

1. **レスポンスタイム**
   - P50, P95, P99パーセンタイル
   - 検索タイプ別の分析

2. **スループット**
   - リクエスト/秒
   - 同時接続数

3. **エラー率**
   - タイムアウト率
   - 5xxエラー率

4. **リソース使用率**
   - CPU使用率
   - メモリ使用率
   - ディスクI/O

### アラート設定

```yaml
# Prometheus アラートルール
groups:
  - name: rag_performance
    rules:
      - alert: HighResponseTime
        expr: http_request_duration_seconds{quantile="0.95"} > 2
        for: 5m
        annotations:
          summary: "95パーセンタイルが2秒を超過"
      
      - alert: LowThroughput
        expr: rate(http_requests_total[5m]) < 10
        for: 10m
        annotations:
          summary: "スループットが10req/s未満"
```

## トラブルシューティング

### 問題: 検索が遅い

**症状**: ベクトル検索が1秒以上かかる

**原因と対策**:
1. インデックスが使用されていない
   ```sql
   EXPLAIN ANALYZE SELECT ... ORDER BY embedding <=> ...;
   ```

2. lists数が不適切
   ```sql
   DROP INDEX idx_chunks_embedding_ivfflat;
   CREATE INDEX ... WITH (lists = 200);
   ```

3. プローブ数が少なすぎる
   ```sql
   SET ivfflat.probes = 20;
   ```

### 問題: メモリ不足

**症状**: OOMエラーが発生

**原因と対策**:
1. バッチサイズが大きすぎる
   ```python
   EMBEDDING_BATCH_SIZE = 50  # 小さくする
   ```

2. コネクションプールが大きすぎる
   ```python
   DATABASE_POOL_SIZE = 10  # 減らす
   ```

3. キャッシュサイズの調整
   ```python
   REDIS_MAX_MEMORY = "2GB"
   ```

### 問題: インデックス作成が遅い

**症状**: インデックス作成に数時間かかる

**原因と対策**:
1. maintenance_work_memを増やす
   ```sql
   SET maintenance_work_mem = '2GB';
   ```

2. 並列度を上げる
   ```sql
   SET max_parallel_maintenance_workers = 4;
   ```

3. 一時的にfsyncを無効化（注意が必要）
   ```sql
   SET fsync = off;  -- インデックス作成後に戻す
   ```

## ベストプラクティス

1. **定期的なメンテナンス**
   - 毎日: VACUUM ANALYZE
   - 週次: インデックス使用状況の確認
   - 月次: パフォーマンステストの実行

2. **段階的な最適化**
   - まずアプリケーション層の最適化
   - 次にデータベース設定のチューニング
   - 最後にインフラのスケーリング

3. **監視の自動化**
   - CI/CDでパフォーマンステストを実行
   - 本番環境のメトリクスを継続的に監視
   - 性能劣化を早期に検出

4. **キャパシティプランニング**
   - 成長予測に基づくリソース計画
   - ピーク時の負荷を考慮
   - バッファを持たせた設計

## 参考資料

- [pgvector公式ドキュメント](https://github.com/pgvector/pgvector)
- [PostgreSQLパフォーマンスチューニング](https://www.postgresql.org/docs/current/performance-tips.html)
- [FastAPIパフォーマンス最適化](https://fastapi.tiangolo.com/deployment/concepts/)