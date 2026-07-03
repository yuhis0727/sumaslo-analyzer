"""
日次更新スクリプト: 毎日正午以降に実行して前日のデータを取得
cron設定例: 0 13 * * * /usr/bin/python3 ~/slot-scraper/daily_update.py >> ~/slot-scraper/logs/daily.log 2>&1
"""
import sys, io, os
from datetime import date, timedelta

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# anaslo_scraperを同じディレクトリからインポート
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from anaslo_scraper import STORES, CHROME_VERSION, IS_VPS, CF_WAIT_MAX, SESSION_RESET_EVERY
import anaslo_scraper as scraper

# 今日・昨日の日付
TODAY     = date.today()
YESTERDAY = TODAY - timedelta(days=1)

print(f"=== 日次更新 {TODAY} ===")
print(f"取得対象: {YESTERDAY}")

# 各店舗を順番に処理
for store_key in STORES:
    store = STORES[store_key]
    csv_path = os.path.expanduser(f"~/slot-scraper/data/anaslo_{store_key}.csv")

    # 昨日のデータが既にあればスキップ
    done = scraper.load_done_dates(csv_path)
    if YESTERDAY.isoformat() in done:
        print(f"[{store['name']}] {YESTERDAY} 取得済み → スキップ")
        continue

    print(f"\n[{store['name']}] 取得開始...")

    # START/END を昨日だけに設定して実行
    scraper.STORE      = store_key
    scraper.START_DATE = YESTERDAY
    scraper.END_DATE   = YESTERDAY
    scraper.OUTPUT_CSV = csv_path

    try:
        scraper.main()
        print(f"[{store['name']}] 完了")
    except Exception as e:
        print(f"[{store['name']}] エラー: {e}")

print(f"\n=== 日次更新完了 ===")
