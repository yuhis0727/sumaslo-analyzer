# Sumaslo Analyzer

マルハンメガシティ2000蒲田7店専用のスロット立ち回り支援ツール。
入場時（抽選番号を引いた直後）に、その番号で狙うべき台を優先順位付きで即座に提示することを目的とした個人用Webアプリです。

## 主な機能

- **ダッシュボード**: 当日のイベント種別・狙い候補TOP5・直近データのブリーフィング
- **台番/機種別分析**: 全台の日別実績（差枚・勝率）をイベント日フィルタ・集計開始日指定つきで閲覧
- **入場シミュレーター**: 抽選番号を入力すると番号帯に応じた狙い台ランキングを提示
- **AIアシスタント「ナナ」**: Claude APIによる立ち回り相談。店長ポスト等の示唆解釈・画像読み取り対応
- **予測検証ループ**: 予測を保存し翌日以降のデータと自動照合、的中率を記録
- **データ自動更新**: みんれぽから毎日スクレイピングしCSVに追記（cron）

## 技術スタック

| 層 | 技術 |
|------|------|
| バックエンド | Python 3.12 / FastAPI / pandas（CSVベース、DBなし） |
| AI | Anthropic Claude API |
| フロントエンド | TypeScript / Next.js 14 / TailwindCSS |
| インフラ | Docker Compose（api / web / nginx）+ VPS |
| スクレイパー | undetected-chromedriver + BeautifulSoup |

## 開発環境セットアップ

```bash
git clone https://github.com/yuhis0727/sumaslo-analyzer.git
cd sumaslo-analyzer

# 環境変数
cp backend/.env.sample backend/.env   # ANTHROPIC_API_KEY を記入

# データCSV（リポジトリ外管理）をリポジトリ直下に配置
# minrepo_maruhan_kamata7_browser.csv

# 起動
docker compose up -d
```

- フロントエンド: http://localhost:3000
- API: http://localhost:8080 （ドキュメント: /docs）

### テスト・lint

```bash
docker compose exec api python3 -m pytest tests/ -q
docker compose exec api ruff check .
docker compose exec web npx tsc --noEmit
```

## ブランチ運用

```
develop で開発（作業ごとに feature/xxx・fix/xxx ブランチを切ってPR→developへマージ）
   ↓ 本番に出したいタイミング
main へマージ（= 本番反映してよい状態の印）
   ↓ 手動デプロイ
VPS で git pull & 再ビルド → 本番反映
```

- 新しい作業は必ず `develop` を pull してからブランチを切る
- `main` へのマージは自動デプロイ**ではない**。反映には下記のデプロイ手順が必要

## 本番デプロイ

本番はVPS上のDocker Compose（`docker-compose.prod.yml`）で稼働。nginx層でBasic認証をかけている。

### 初回構築

```bash
# VPS上で
git clone -b main https://github.com/yuhis0727/sumaslo-analyzer.git
cd sumaslo-analyzer

cp backend/.env.production.sample backend/.env   # ANTHROPIC_API_KEY を記入
cp .env.production.sample .env                   # NEXT_PUBLIC_API_URL=http://<VPSのIP> に書き換え

# Basic認証ファイルを生成（リポジトリにはコミットしない）
PW=<任意のパスワード>
echo "ユーザー名:$(openssl passwd -apr1 $PW)" > docker/nginx/.htpasswd

# データCSVを配置（ローカルからscp等で）
# minrepo_maruhan_kamata7_browser.csv をリポジトリ直下に

docker compose -f docker-compose.prod.yml up -d --build
```

低メモリVPS（1GB等）ではビルド前にスワップの追加が必要:

```bash
sudo fallocate -l 4G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

ファイアウォールはVPS内iptablesとクラウド側（Oracle Cloudならセキュリティリスト）の**両方**でポート80/443を開放すること。

### 更新反映（通常のデプロイ）

```bash
# VPS上で
cd ~/sumaslo-analyzer
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

`NEXT_PUBLIC_API_URL` はビルド時にフロントへ埋め込まれるため、URL変更時は必ず `--build` 付きで再実行する。

### データ自動更新（cron）

`scripts/scraper.py` は日付を自動計算する（前日までの直近7日分を対象、取得済み日はスキップ）。
APIはCSVをメモリキャッシュするため、**スクレイプ後にapiコンテナの再起動が必要**。

```cron
0 13 * * * cd ~/sumaslo-analyzer && python3 scripts/scraper.py >> ~/scraper.log 2>&1 && docker compose -f docker-compose.prod.yml restart api
```

※ VPSのタイムゾーンをJSTにしておくこと（`sudo timedatectl set-timezone Asia/Tokyo`）。
スクレイパー実行にはVPSホスト側にChromium/Xvfb/Python依存が必要（`vps_setup.sh` 参照）。

### ドメイン取得後（SSL化）

1. DNSをVPSのIPに向ける
2. certbot等で証明書を取得
3. `docker/nginx/nginx.conf` 内にコメントで温存してあるSSL用server blockを有効化
4. ルート `.env` の `NEXT_PUBLIC_API_URL` をhttpsのURLに変更して `--build` 付きで再デプロイ

## 注意事項

- **個人利用限定**: このツールは個人的な分析用途でのみ使用
- **スクレイピング**: 取得先の利用規約を遵守し、適切な間隔でリクエストする
- **秘匿情報**: APIキー・Basic認証情報・本番IPはリポジトリにコミットしない（`.env` / `.htpasswd` はgitignore済み）
