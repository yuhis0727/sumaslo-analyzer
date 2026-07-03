"""
みんれぽ VPS用スクレイパー
- URLリスト収集: httpx（軽量・高速）
- データ取得: Chromium + Xvfb（ベースページ→?kishu=allクリック）
- Cloudflareなしなのでヘッドレスブラウザで問題なし
"""
import sys, io, re, csv, time, os, platform
from datetime import date, timedelta

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

import httpx
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

# ------------------------------------------------------------------ #
# 設定
# ------------------------------------------------------------------ #
STORE = "maruhan_kamata7"
TAG_URL = "https://min-repo.com/tag/%e3%83%9e%e3%83%ab%e3%83%8f%e3%83%b3%e3%83%a1%e3%82%ac%e3%82%b7%e3%83%86%e3%82%a32000%e8%92%b2%e7%94%b07/"
START_DATE = date(2026, 6, 19)
END_DATE   = date(2026, 7, 2)
OUTPUT_CSV = f"minrepo_{STORE}_browser.csv"
TODAY      = date(2026, 7, 3)
HEADERS    = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

IS_VPS = (platform.system() == "Linux" and not os.environ.get("DISPLAY"))
CHROME_VERSION = 149 if IS_VPS else 148

# ------------------------------------------------------------------ #
# Step1: httpxでURLリスト収集（タグページから全日付を取得）
# ------------------------------------------------------------------ #
def collect_date_urls() -> list[tuple[date, str]]:
    print("=== Step1: URLリスト収集 (httpx) ===")
    result = []
    page = 1
    latest_seen = TODAY

    with httpx.Client(headers=HEADERS, follow_redirects=True) as client:
        while True:
            url = TAG_URL if page == 1 else TAG_URL + f"page/{page}/"
            r = client.get(url, timeout=30)
            if r.status_code != 200:
                break

            soup = BeautifulSoup(r.text, "html.parser")
            found = 0
            exceeded = False

            for a in soup.find_all("a", href=re.compile(r"min-repo\.com/\d+/$")):
                text = a.get_text(strip=True)
                m = re.search(r"(\d{1,2})/(\d{1,2})", text)
                if not m:
                    continue
                month, day = int(m.group(1)), int(m.group(2))
                for year in [latest_seen.year, latest_seen.year - 1]:
                    try:
                        d = date(year, month, day)
                        if d <= latest_seen:
                            latest_seen = d
                            found += 1
                            if d < START_DATE:
                                exceeded = True
                            elif d <= END_DATE:
                                result.append((d, a["href"]))
                            break
                    except ValueError:
                        continue

            print(f"  page {page}: {found}件 | 収集済み {len(result)}件 | 最古 {latest_seen}", flush=True)
            if exceeded or found == 0:
                break
            page += 1

    result.sort(key=lambda x: x[0])
    print(f"→ 対象: {len(result)}日分\n")
    return result


# ------------------------------------------------------------------ #
# Step2: Chromiumでデータ取得
# ------------------------------------------------------------------ #
def parse_kishu_all(html: str, target_date: date) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    for table in soup.find_all("table"):
        ths = [th.get_text(strip=True) for th in table.find_all("th")]
        if "台番" in ths and "差枚" in ths:
            rows = table.find_all("tr")
            results = []
            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 4:
                    continue
                def clean_int(text):
                    cleaned = re.sub(r"[^\d\-]", "", text.strip())
                    try:
                        return int(cleaned) if cleaned and cleaned != "-" else None
                    except ValueError:
                        return None
                results.append({
                    "date":           target_date.isoformat(),
                    "model_name":     cols[0].get_text(strip=True),
                    "machine_number": clean_int(cols[1].text),
                    "total_diff":     clean_int(cols[2].text),
                    "game_count":     clean_int(cols[3].text),
                    "rate":           cols[4].get_text(strip=True) if len(cols) > 4 else None,
                })
            return results
    return []


def get_done_dates() -> set[str]:
    """既にCSVに保存済みの日付セットを返す（チェックポイント用）"""
    if not os.path.exists(OUTPUT_CSV):
        return set()
    done = set()
    with open(OUTPUT_CSV, encoding="utf-8-sig") as f:
        for line in f:
            parts = line.strip().split(",")
            if parts and len(parts[0]) == 10 and parts[0][0].isdigit():
                done.add(parts[0])
    return done


def scrape_all(date_urls: list[tuple[date, str]]):
    done = get_done_dates()
    if done:
        before = len(date_urls)
        date_urls = [(d, u) for d, u in date_urls if d.isoformat() not in done]
        print(f"チェックポイント: {len(done)}日分スキップ → 残り{len(date_urls)}日分\n")
    if not date_urls:
        print("全日付取得済み。終了。")
        return

    if IS_VPS:
        os.environ["DISPLAY"] = ":99"
        print("VPS環境 → DISPLAY=:99 (Xvfb)")

    options = uc.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    if IS_VPS:
        options.binary_location = "/usr/bin/chromium-browser"

    driver = uc.Chrome(options=options, use_subprocess=True, version_main=CHROME_VERSION)

    # 先にトップページを1回開いてセッションを確立
    driver.get("https://min-repo.com/")
    time.sleep(2)

    fields = ["date", "model_name", "machine_number", "total_diff", "game_count", "rate"]
    csv_exists = os.path.exists(OUTPUT_CSV)
    csvfile = open(OUTPUT_CSV, "a", newline="", encoding="utf-8-sig")
    writer = csv.DictWriter(csvfile, fieldnames=fields)
    if not csv_exists:
        writer.writeheader()

    total = len(date_urls)
    total_rows = 0
    t0 = time.time()

    print(f"=== Step2: {total}日分 ブラウザ取得開始 ===\n")

    for i, (target_date, base_url) in enumerate(date_urls, 1):
        page_t = time.time()
        try:
            # ベースページへ移動
            driver.get(base_url)
            time.sleep(2)

            # ?kishu=all リンクをクリック
            btn = driver.find_element(By.XPATH, "//a[contains(@href, 'kishu=all')]")
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(3)

            rows = parse_kishu_all(driver.page_source, target_date)
            if rows:
                writer.writerows(rows)
                csvfile.flush()
                total_rows += len(rows)
                status = f"{len(rows)}台"
            else:
                status = "データなし"

        except Exception as e:
            status = f"ERR:{str(e)[:30]}"

        elapsed = time.time() - t0
        page_sec = time.time() - page_t
        eta = elapsed / i * (total - i)
        print(f"  [{i:3d}/{total}] {target_date} | {status:12s} | {page_sec:4.1f}s/p | 残:{eta:4.0f}s", flush=True)

    driver.quit()
    csvfile.close()
    print(f"\n完了! {total_rows:,}行 → {OUTPUT_CSV} ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    date_urls = collect_date_urls()
    if date_urls:
        scrape_all(date_urls)
