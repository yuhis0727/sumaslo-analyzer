"""
アナスロスクレイピングのテストスクリプト
ローカル（Windows）で実行してCloudflare突破を確認

手順:
1. まずデータ一覧ページにアクセス（Cloudflare認証を通過）
2. 日付リンクをクリックして詳細ページに移動
3. データを取得
"""
import sys
import time
sys.path.insert(0, 'backend/src')

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup


def test_scrape():
    # データ一覧ページ（ここでCloudflare認証を通過）
    list_url = "https://ana-slo.com/%E3%83%9B%E3%83%BC%E3%83%AB%E3%83%87%E3%83%BC%E3%82%BF/%E6%9D%B1%E4%BA%AC%E9%83%BD/%E3%83%9E%E3%83%AB%E3%83%8F%E3%83%B3%E3%83%A1%E3%82%AC%E3%82%B7%E3%83%86%E3%82%A32000-%E8%92%B2%E7%94%B07-%E3%83%87%E3%83%BC%E3%82%BF%E4%B8%80%E8%A6%A7/"

    # クリックする日付リンク
    date_link_text = "2026/01/14"

    print("=" * 60)
    print("アナスロ スクレイピングテスト（2段階アクセス）")
    print("=" * 60)
    print(f"Step1: データ一覧ページ → Cloudflare認証通過")
    print(f"Step2: 日付リンクをクリック → 詳細データ取得")
    print()

    # ブラウザ起動
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    driver = uc.Chrome(options=options, use_subprocess=True)

    try:
        # Step 1: データ一覧ページにアクセス
        print("Step1: データ一覧ページにアクセス中...")
        driver.get(list_url)

        # Cloudflare認証待機（15秒）
        print("Cloudflare認証を待機中...（15秒）")
        time.sleep(15)

        # ページ読み込み確認
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        print("データ一覧ページ読み込み完了！")
        print()

        # Step 2: 日付リンクをクリック
        print(f"Step2: 日付リンク「{date_link_text}」を探してクリック...")

        # 日付リンクを探す（部分一致）
        date_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "2026/01/14")

        if date_links:
            print(f"日付リンクを発見！クリックします...")

            # 広告オーバーレイを閉じる試み
            try:
                overlay = driver.find_element(By.ID, "overlay_ads_area")
                driver.execute_script("arguments[0].style.display = 'none';", overlay)
                print("広告オーバーレイを非表示にしました")
            except:
                pass

            # 現在のウィンドウハンドルを保存
            original_window = driver.current_window_handle
            original_handles = driver.window_handles

            # JavaScriptでクリック（広告を回避）
            driver.execute_script("arguments[0].click();", date_links[0])

            # ページ遷移を待機
            time.sleep(3)

            # 新しいタブが開いたかチェック
            new_handles = driver.window_handles
            if len(new_handles) > len(original_handles):
                # 新しいタブに切り替え
                for handle in new_handles:
                    if handle != original_window:
                        driver.switch_to.window(handle)
                        print("新しいタブに切り替えました！")
                        break

            # さらに待機
            time.sleep(5)
            print(f"現在のURL: {driver.current_url}")
            print("詳細ページに移動しました！")
        else:
            print("日付リンクが見つかりません。別の方法を試します...")
            # 直接URLでアクセス（認証済みの状態で）
            detail_url = "https://ana-slo.com/2026-01-14-%e3%83%9e%e3%83%ab%e3%83%8f%e3%83%b3%e3%83%a1%e3%82%ac%e3%82%b7%e3%83%86%e3%82%a32000-%e8%92%b2%e7%94%b07-data/"
            driver.get(detail_url)
            time.sleep(5)

        # Step 3: データ取得
        print()
        print("Step3: データを取得中...")

        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")

        # 店舗名取得
        title = soup.find("title")
        store_name = "不明"
        if title:
            store_name = title.text.strip()
        print(f"ページタイトル: {store_name}")

        # テーブル取得（複数のセレクタを試す）
        table = soup.find("table", id="all_data_table")
        if not table:
            table = soup.find("table", class_="fixed_get_medals_table")

        # table-data-cellクラスを持つ要素を探す
        data_cells = soup.find_all(class_="table-data-cell")
        print(f"table-data-cell クラスの要素数: {len(data_cells)}")

        if table:
            tbody = table.find("tbody")
            rows = tbody.find_all("tr") if tbody else table.find_all("tr")[1:]

            print(f"取得台数: {len(rows)}台")
            print()
            print("【サンプルデータ（最初の5台）】")
            print("-" * 60)

            for i, row in enumerate(rows[:5]):
                cols = row.find_all("td")
                if len(cols) >= 6:
                    print(f"{i+1}. {cols[0].text.strip()}")
                    print(f"   台番号: {cols[1].text.strip()}")
                    print(f"   G数: {cols[2].text.strip()}")
                    print(f"   差枚: {cols[3].text.strip()}")
                    print(f"   BB: {cols[4].text.strip()} / RB: {cols[5].text.strip()}")
                    print()
        elif data_cells:
            print(f"table-data-cellからデータ取得を試みます...")
            print()
            print("【サンプルデータ（最初の10セル）】")
            print("-" * 60)
            for i, cell in enumerate(data_cells[:10]):
                print(f"  セル{i+1}: {cell.text.strip()}")
        else:
            print("警告: テーブルが見つかりません")
            print()
            print("ページのHTMLを確認...")
            # デバッグ用：ページ内のテーブルを確認
            all_tables = soup.find_all("table")
            print(f"見つかったテーブル数: {len(all_tables)}")
            for i, t in enumerate(all_tables):
                print(f"  テーブル{i+1}: id={t.get('id')}, class={t.get('class')}")

        print()
        print("=" * 60)
        print("テスト完了！")
        print("=" * 60)

    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("ブラウザを閉じます...")
        driver.quit()


if __name__ == "__main__":
    test_scrape()
