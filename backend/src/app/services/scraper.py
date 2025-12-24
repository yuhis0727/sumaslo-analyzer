import re
from datetime import datetime
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service


class AnasloScraper:
    """アナスロからデータをスクレイピングするクラス"""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None

    def _setup_driver(self):
        """Selenium WebDriverのセットアップ"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

    def _close_driver(self):
        """WebDriverのクローズ"""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def scrape_store_data(self, store_url: str) -> Dict:
        """
        店舗のページから台データを取得

        Args:
            store_url: アナスロの店舗URL

        Returns:
            店舗データと台データを含む辞書
        """
        try:
            self._setup_driver()
            self.driver.get(store_url)

            # ページの読み込みを待機
            WebDriverWait(self.driver, 10).until(
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
        # アナスロのHTMLから店舗名を取得
        # 実際のHTML構造に応じて調整が必要
        store_name_elem = soup.find("h1", class_="store-name")
        if store_name_elem:
            return store_name_elem.text.strip()

        # フォールバック: titleタグから取得
        title = soup.find("title")
        if title:
            return title.text.strip().split("|")[0].strip()

        return "不明な店舗"

    def _extract_machines_data(self, soup: BeautifulSoup) -> List[Dict]:
        """台データを抽出"""
        machines = []

        # アナスロの台データテーブルを取得
        # 実際のHTML構造に応じて調整が必要
        table = soup.find("table", class_="machine-data")
        if not table:
            # 別のセレクタを試す
            table = soup.find("table", id="dataTable")

        if table:
            rows = table.find_all("tr")[1:]  # ヘッダー行をスキップ

            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 5:
                    machine_data = self._parse_machine_row(cols)
                    if machine_data:
                        machines.append(machine_data)

        return machines

    def _parse_machine_row(self, cols) -> Optional[Dict]:
        """台データの行をパース"""
        try:
            # 実際のHTML構造に応じて調整が必要
            # 例: 台番号, 機種名, ゲーム数, BB, RB, 差枚数
            machine_number = self._extract_number(cols[0].text)
            model_name = cols[1].text.strip()
            game_count = self._extract_number(cols[2].text)
            big_bonus = self._extract_number(cols[3].text) if len(cols) > 3 else None
            regular_bonus = self._extract_number(cols[4].text) if len(cols) > 4 else None
            total_difference = (
                self._extract_number(cols[5].text) if len(cols) > 5 else None
            )

            return {
                "machine_number": machine_number,
                "model_name": model_name,
                "game_count": game_count,
                "big_bonus": big_bonus,
                "regular_bonus": regular_bonus,
                "art_count": None,  # 必要に応じて追加
                "total_difference": total_difference,
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
