# Sumaslo Analyzer

スマスロのデータを分析し、AIが高設定台の可能性がある店舗を予測するWebアプリケーションです。

## 概要

アナスロから店舗の台データをスクレイピングし、ディープラーニングを使用して高設定台が入りやすい場所を分析・予測します。

### 主な機能

- **データスクレイピング**: アナスロの店舗ページから台データを自動取得
- **AI分析**: PyTorchベースのディープラーニングモデルで高設定台を予測
- **統計分析**: ゲーム数、差枚数、ボーナス回数などの統計情報を可視化
- **おすすめ台表示**: 高設定の可能性が高い台番号を推奨
- **自動更新**: 1日1回の自動データ更新(予定)

## 技術スタック

### バックエンド

| 技術 | バージョン | 用途 |
|------|-----------|------|
| Python | 3.12 | メイン言語 |
| FastAPI | 0.109.2 | WebAPIフレームワーク |
| PyTorch | 2.5.1 | ディープラーニング |
| Selenium | 4.27.1 | Webスクレイピング |
| SQLAlchemy | 2.0.32 | ORM |
| MySQL | 8.0 | データベース |
| Pandas | 2.2.3 | データ処理 |
| NumPy | 2.2.1 | 数値計算 |

### フロントエンド

| 技術 | バージョン | 用途 |
|------|-----------|------|
| TypeScript | 5.3.3 | メイン言語 |
| Next.js | 14.0.4 | Reactフレームワーク |
| React | 18.2.0 | UIライブラリ |
| TailwindCSS | 3.4.0 | CSSフレームワーク |

## セットアップ

### 前提条件

- Docker & Docker Compose
- Node.js 20.x
- Python 3.12

### インストール

1. リポジトリをクローン

```bash
git clone https://github.com/yourusername/sumaslo-analyzer.git
cd sumaslo-analyzer
```

2. 環境変数を設定

```bash
cp backend/.env.sample backend/.env
cp frontend/.env.local.sample frontend/.env.local
```

3. hostsファイルを設定 (`/etc/hosts` または `C:\Windows\System32\drivers\etc\hosts`)

```
127.0.0.1 sumaslo-analyzer.dev
127.0.0.1 api.sumaslo-analyzer.dev
```

4. Dockerコンテナを起動

```bash
docker compose up -d
```

5. データベースマイグレーション

```bash
docker compose exec api alembic upgrade head
```

### アクセス

- フロントエンド: http://sumaslo-analyzer.dev
- API ドキュメント: http://api.sumaslo-analyzer.dev/docs
- データベース: localhost:13306

## 使い方

### 1. 店舗を登録

APIまたはフロントエンドから店舗情報を登録します。

```bash
curl -X POST http://api.sumaslo-analyzer.dev/api/v1/slots/stores \
  -H "Content-Type: application/json" \
  -d '{
    "name": "店舗名",
    "area": "エリア名",
    "anaslo_url": "https://..."
  }'
```

### 2. データをスクレイピング

登録した店舗のデータを取得します。

```bash
curl -X POST http://api.sumaslo-analyzer.dev/api/v1/slots/scrape/{store_id}
```

### 3. データを分析

AIが店舗データを分析し、高設定台の確率を予測します。

```bash
curl -X POST http://api.sumaslo-analyzer.dev/api/v1/slots/analyze/{store_id}
```

### 4. フロントエンドで確認

http://sumaslo-analyzer.dev/analysis にアクセスして、視覚的に分析結果を確認できます。

## API エンドポイント

### 店舗管理

- `GET /api/v1/slots/stores` - 店舗一覧取得
- `GET /api/v1/slots/stores/{store_id}` - 店舗詳細取得
- `POST /api/v1/slots/stores` - 店舗登録

### データ取得・分析

- `POST /api/v1/slots/scrape/{store_id}` - スクレイピング実行
- `POST /api/v1/slots/analyze/{store_id}` - AI分析実行
- `GET /api/v1/slots/predictions/{store_id}` - 予測履歴取得
- `GET /api/v1/slots/scraping-logs/{store_id}` - スクレイピングログ取得

## データベーススキーマ

### stores (店舗)

- id: 店舗ID
- name: 店舗名
- area: エリア
- anaslo_url: アナスロURL

### slot_machines (台データ)

- id: データID
- store_id: 店舗ID
- machine_number: 台番号
- model_name: 機種名
- game_count: ゲーム数
- big_bonus: BB回数
- regular_bonus: RB回数
- art_count: ART回数
- total_difference: 差枚数
- data_date: データ取得日

### predictions (AI予測結果)

- id: 予測ID
- store_id: 店舗ID
- prediction_date: 予測日
- high_setting_probability: 高設定台の確率
- confidence_score: 信頼度スコア
- recommended_machines: おすすめ台番号
- analysis_details: 分析詳細

## AI分析の仕組み

1. **特徴量抽出**: ゲーム数、ボーナス回数、差枚数などから特徴量を算出
2. **統計分析**: 平均値、標準偏差、高パフォーマンス台の割合を計算
3. **ニューラルネットワーク**: PyTorchベースのモデルで高設定確率を予測
4. **総合評価**: 統計分析とAI予測を組み合わせて最終スコアを算出

## 注意事項

- **個人利用限定**: このツールは個人的な分析用途でのみ使用してください
- **スクレイピング**: アナスロの利用規約を遵守し、適切な間隔でリクエストを行ってください
- **予測精度**: AI予測はあくまで参考情報であり、実際の設定を保証するものではありません
- **責任**: このツールの使用によって生じた損失について、開発者は一切責任を負いません

## ライセンス

このプロジェクトは個人利用を想定しています。

## 開発者

開発に関する質問や提案は、GitHubのIssuesでお願いします。

## TODO

- [ ] 定期実行機能の実装(Celery)
- [ ] AIモデルの学習データ収集
- [ ] 機種別の分析機能
- [ ] 履歴グラフ表示
- [ ] ユーザー認証機能
- [ ] モバイル対応の改善
