import re
import time
from datetime import datetime
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class AnasloScraper:
    """アナスロからデータをスクレイピングするクラス（Cloudflare対応）"""

    def __init__(self, headless: bool = False):
        # undetected-chromedriverはheadlessだと検出されやすいのでデフォルトFalse
        self.headless = headless
        self.driver = None

    def _setup_driver(self):
        """undetected-chromedriver のセットアップ（Cloudflare回避）"""
        options = uc.ChromeOptions()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")

        self.driver = uc.Chrome(options=options, use_subprocess=True)

    def _close_driver(self):
        """WebDriverのクローズ"""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def scrape_store_data_by_date(
        self,
        list_url: str,
        target_date: str,
        wait_for_cloudflare: int = 15
    ) -> Dict:
        """
        2段階アクセスで店舗の日付別データを取得（Cloudflare対応）

        Args:
            list_url: データ一覧ページのURL
            target_date: 取得したい日付（例: "2026/01/14"）
            wait_for_cloudflare: Cloudflare認証待機秒数

        Returns:
            店舗データと台データを含む辞書
        """
        try:
            self._setup_driver()

            # Step 1: データ一覧ページにアクセス（Cloudflare認証を通過）
            self.driver.get(list_url)
            time.sleep(wait_for_cloudflare)

            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Step 2: 日付リンクをクリック
            date_links = self.driver.find_elements(By.PARTIAL_LINK_TEXT, target_date)

            if not date_links:
                raise Exception(f"日付リンクが見つかりません: {target_date}")

            # 広告オーバーレイを非表示にする
            try:
                overlay = self.driver.find_element(By.ID, "overlay_ads_area")
                self.driver.execute_script("arguments[0].style.display = 'none';", overlay)
            except:
                pass

            # 現在のウィンドウハンドルを保存
            original_window = self.driver.current_window_handle
            original_handles = self.driver.window_handles

            # JavaScriptでクリック（広告を回避）
            self.driver.execute_script("arguments[0].click();", date_links[0])
            time.sleep(3)

            # 新しいタブが開いたかチェック
            new_handles = self.driver.window_handles
            if len(new_handles) > len(original_handles):
                for handle in new_handles:
                    if handle != original_window:
                        self.driver.switch_to.window(handle)
                        break

            time.sleep(5)

            # Step 3: データ取得
            html = self.driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            store_name = self._extract_store_name(soup)
            machines_data = self._extract_machines_data(soup)

            return {
                "store_name": store_name,
                "store_url": self.driver.current_url,
                "data_date": datetime.now(),
                "target_date": target_date,
                "machines": machines_data,
            }

        except Exception as e:
            raise Exception(f"スクレイピングエラー: {str(e)}")
        finally:
            self._close_driver()

    def scrape_store_data(self, store_url: str, wait_for_cloudflare: int = 10) -> Dict:
        """
        店舗のページから台データを取得（直接アクセス版 - Cloudflare認証済みの場合のみ）

        Args:
            store_url: アナスロの店舗URL
            wait_for_cloudflare: Cloudflare認証待機秒数

        Returns:
            店舗データと台データを含む辞書
        """
        try:
            self._setup_driver()
            self.driver.get(store_url)

            # Cloudflareチャレンジを通過するまで待機
            time.sleep(wait_for_cloudflare)

            # ページの読み込みを待機
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # ページソースを取得
            html = self.driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            # 店舗名を取得
            store_name = self._extract_store_name(soup)

            # 台データを取得
            machines_data = self._extract_machines_data(soup)

            return {
                "store_name": store_name,
                "store_url": store_url,
                "data_date": datetime.now(),
                "machines": machines_data,
            }

        except Exception as e:
            raise Exception(f"スクレイピングエラー: {str(e)}")
        finally:
            self._close_driver()

    def _extract_store_name(self, soup: BeautifulSoup) -> str:
        """店舗名を抽出"""
        # titleタグから店舗名を取得（例: "2026-01-14 マルハン... | アナスロ"）
        title = soup.find("title")
        if title:
            title_text = title.text.strip()
            # "日付 店舗名 data | アナスロ" の形式から店舗名を抽出
            if "|" in title_text:
                title_part = title_text.split("|")[0].strip()
                # 日付部分を除去 (YYYY-MM-DD 形式)
                parts = title_part.split(" ", 1)
                if len(parts) > 1 and "-" in parts[0]:
                    return parts[1].replace("-data", "").replace("data", "").strip()
                return title_part
        return "不明な店舗"

    def _extract_machines_data(self, soup: BeautifulSoup) -> List[Dict]:
        """台データを抽出（アナスロの日付詳細ページ用）"""
        machines = []

        # アナスロの台データテーブルを取得
        # id="all_data_table" または class="fixed_get_medals_table"
        table = soup.find("table", id="all_data_table")
        if not table:
            table = soup.find("table", class_="fixed_get_medals_table")

        if table:
            tbody = table.find("tbody")
            if tbody:
                rows = tbody.find_all("tr")
            else:
                rows = table.find_all("tr")[1:]  # ヘッダー行をスキップ

            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 6:  # 最低限必要なカラム数
                    machine_data = self._parse_machine_row(cols)
                    if machine_data:
                        machines.append(machine_data)

        return machines

    def _parse_machine_row(self, cols) -> Optional[Dict]:
        """台データの行をパース（アナスロ形式）"""
        try:
            # アナスロのカラム順序:
            # 0: 機種名, 1: 台番号, 2: G数, 3: 差枚, 4: BB, 5: RB,
            # 6: 合成確率, 7: BB確率, 8: RB確率
            model_name = cols[0].text.strip()
            machine_number = self._extract_number(cols[1].text)
            game_count = self._extract_number(cols[2].text)
            total_difference = self._extract_number(cols[3].text)
            big_bonus = self._extract_number(cols[4].text) if len(cols) > 4 else None
            regular_bonus = self._extract_number(cols[5].text) if len(cols) > 5 else None

            # 確率データ（オプション）
            combined_rate = cols[6].text.strip() if len(cols) > 6 else None
            bb_rate = cols[7].text.strip() if len(cols) > 7 else None
            rb_rate = cols[8].text.strip() if len(cols) > 8 else None

            return {
                "machine_number": machine_number,
                "model_name": model_name,
                "game_count": game_count,
                "big_bonus": big_bonus,
                "regular_bonus": regular_bonus,
                "art_count": None,
                "total_difference": total_difference,
                "combined_rate": combined_rate,
                "bb_rate": bb_rate,
                "rb_rate": rb_rate,
            }
        except Exception as e:
            print(f"台データのパースエラー: {e}")
            return None

    def _extract_number(self, text: str) -> Optional[int]:
        """テキストから数値を抽出"""
        if not text:
            return None

        # カンマや空白を除去して数値のみを抽出
        cleaned = re.sub(r"[^\d-]", "", text.strip())
        if cleaned and cleaned != "-":
            try:
                return int(cleaned)
            except ValueError:
                return None
        return None

    def search_stores(self, area: str = None, keyword: str = None) -> List[Dict]:
        """
        店舗を検索

        Args:
            area: エリア名
            keyword: 検索キーワード

        Returns:
            店舗情報のリスト
        """
        # アナスロの検索機能を使用して店舗を検索
        # 実装は実際のサイト構造に応じて調整
        stores = []
        # TODO: 実際の検索ロジックを実装
        return stores
