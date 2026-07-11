"""自動更新スケジューラ (APScheduler)

CLAUDE.md:
  UPDATE_HOUR = 12  # 毎日12時に更新（営業終了後のデータが揃う時間）
  SCRAPE_INTERVAL_SECONDS = 2.5   # アクセス間隔
  MAX_RETRIES = 3                  # 最大リトライ回数
  TIMEOUT_SECONDS = 30             # タイムアウト

使い方:
  from src.app.services.scheduler import start_scheduler, stop_scheduler

  # FastAPI lifespan で呼び出す
  start_scheduler()
  ...
  stop_scheduler()
"""

import time
from datetime import date, datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

UPDATE_HOUR = 12  # 毎日12時に更新（営業終了後のデータが揃う時間）

# アクセス間隔 (スクレイピング規約遵守)
_SCRAPE_INTERVAL = 2.5
_MAX_RETRIES = 3

_scheduler = BackgroundScheduler(timezone="Asia/Tokyo")


def _scrape_all_stores() -> None:
    """登録済み全店舗の前日データをスクレイピングする"""
    from src.app.models import SessionLocal
    from src.app.models.slot_data import ScrapingLog, Store
    from src.app.services.scraper import AnasloScraper
    from src.app.models.slot_data import Machine

    db = SessionLocal()
    try:
        stores = db.query(Store).filter(Store.url.isnot(None)).all()
        target_date_str = (date.today() - timedelta(days=1)).strftime("%Y/%m/%d")

        for store in stores:
            log = ScrapingLog(
                store_id=store.id,
                status="running",
                started_at=datetime.now(),
            )
            db.add(log)
            db.commit()
            db.refresh(log)

            for attempt in range(1, _MAX_RETRIES + 1):
                try:
                    scraper = AnasloScraper(headless=True)
                    data = scraper.scrape_store_data_by_date(
                        list_url=store.url,
                        target_date=target_date_str,
                    )
                    scraped_date = (date.today() - timedelta(days=1))

                    for machine in data.get("machines", []):
                        if machine.get("machine_number") is None:
                            continue
                        db.add(
                            Machine(
                                store_id=store.id,
                                machine_number=machine["machine_number"],
                                model_name=machine.get("model_name", "不明"),
                                date=scraped_date,
                                games_played=machine.get("game_count"),
                                diff_medals=machine.get("total_difference"),
                                bonus_count=(
                                    (machine.get("big_bonus") or 0)
                                    + (machine.get("regular_bonus") or 0)
                                ),
                                reg_count=machine.get("regular_bonus"),
                                big_count=machine.get("big_bonus"),
                                at_count=machine.get("art_count"),
                            )
                        )

                    log.status = "success"
                    log.scraped_count = len(data.get("machines", []))
                    log.completed_at = datetime.now()
                    db.commit()
                    break  # 成功したらリトライ不要

                except Exception as e:
                    if attempt == _MAX_RETRIES:
                        log.status = "failed"
                        log.error_message = str(e)
                        log.completed_at = datetime.now()
                        db.commit()
                    else:
                        # エクスポネンシャルバックオフ
                        wait = _SCRAPE_INTERVAL * (2 ** attempt)
                        time.sleep(wait)

            # 店舗間のアクセス間隔を確保
            time.sleep(_SCRAPE_INTERVAL)

    finally:
        db.close()


def start_scheduler() -> None:
    """スケジューラを起動する (アプリ起動時に呼び出す)"""
    if _scheduler.running:
        return

    # 毎日 UPDATE_HOUR 時 (デフォルト 12:00) に全店舗をスクレイピング
    _scheduler.add_job(
        _scrape_all_stores,
        trigger=CronTrigger(hour=UPDATE_HOUR, minute=0, timezone="Asia/Tokyo"),
        id="daily_scrape",
        replace_existing=True,
        misfire_grace_time=3600,  # 1時間以内なら遅延実行
    )

    _scheduler.start()
    print(f"[Scheduler] 起動完了 — 毎日 {UPDATE_HOUR:02d}:00 に自動スクレイピングを実行します")


def stop_scheduler() -> None:
    """スケジューラを停止する (アプリ終了時に呼び出す)"""
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        print("[Scheduler] 停止しました")
