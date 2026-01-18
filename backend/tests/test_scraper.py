"""AnasloScraperクラスのユニットテスト

このテストファイルはスクレイパーの内部ロジック（パース処理等）をテストします。
実際のウェブスクレイピングは外部サービスに依存するため、モックを使用します。
"""
import os
import sys

import pytest
from bs4 import BeautifulSoup

# Docker環境とローカル環境の両方に対応
src_path = os.path.join(os.path.dirname(__file__), "..", "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from app.services.scraper import AnasloScraper


class TestExtractNumber:
    """_extract_number メソッドのテスト"""

    def setup_method(self):
        self.scraper = AnasloScraper()

    def test_extract_positive_number(self):
        """正の数を正しく抽出できる"""
        assert self.scraper._extract_number("1234") == 1234
        assert self.scraper._extract_number("100") == 100

    def test_extract_negative_number(self):
        """負の数を正しく抽出できる"""
        assert self.scraper._extract_number("-500") == -500
        assert self.scraper._extract_number("-1234") == -1234

    def test_extract_number_with_comma(self):
        """カンマ区切りの数を正しく抽出できる"""
        assert self.scraper._extract_number("1,234") == 1234
        assert self.scraper._extract_number("10,000") == 10000
        assert self.scraper._extract_number("-1,234") == -1234

    def test_extract_number_with_spaces(self):
        """空白を含む文字列から数を正しく抽出できる"""
        assert self.scraper._extract_number(" 100 ") == 100
        assert self.scraper._extract_number("  -500  ") == -500

    def test_extract_number_empty_string(self):
        """空文字列の場合はNoneを返す"""
        assert self.scraper._extract_number("") is None
        assert self.scraper._extract_number("   ") is None

    def test_extract_number_dash_only(self):
        """ダッシュのみの場合はNoneを返す"""
        assert self.scraper._extract_number("-") is None

    def test_extract_number_none_input(self):
        """None入力の場合はNoneを返す"""
        assert self.scraper._extract_number(None) is None

    def test_extract_number_non_numeric(self):
        """数字を含まない文字列の場合はNoneを返す"""
        assert self.scraper._extract_number("abc") is None


class TestExtractStoreName:
    """_extract_store_name メソッドのテスト"""

    def setup_method(self):
        self.scraper = AnasloScraper()

    def test_extract_store_name_standard_format(self):
        """標準的なタイトル形式から店舗名を抽出できる"""
        html = """
        <html>
        <head><title>2026-01-14 マルハン蒲田7-data | アナスロ</title></head>
        <body></body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = self.scraper._extract_store_name(soup)
        assert "マルハン" in result
        assert "アナスロ" not in result

    def test_extract_store_name_no_date(self):
        """日付なしのタイトルから店舗名を抽出できる"""
        html = """
        <html>
        <head><title>マルハン新宿 | アナスロ</title></head>
        <body></body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = self.scraper._extract_store_name(soup)
        assert "マルハン新宿" in result

    def test_extract_store_name_no_title(self):
        """タイトルタグがない場合はデフォルト値を返す"""
        html = """
        <html>
        <head></head>
        <body></body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = self.scraper._extract_store_name(soup)
        assert result == "不明な店舗"


class TestExtractMachinesData:
    """_extract_machines_data メソッドのテスト"""

    def setup_method(self):
        self.scraper = AnasloScraper()

    def test_extract_machines_from_all_data_table(self):
        """all_data_table IDからデータを抽出できる"""
        html = """
        <html>
        <body>
        <table id="all_data_table">
            <tbody>
                <tr>
                    <td>バジリスク絆2</td>
                    <td>101</td>
                    <td>5,000</td>
                    <td>+1,500</td>
                    <td>10</td>
                    <td>5</td>
                    <td>1/333</td>
                    <td>1/500</td>
                    <td>1/1000</td>
                </tr>
                <tr>
                    <td>まどマギ叛逆</td>
                    <td>102</td>
                    <td>3,000</td>
                    <td>-500</td>
                    <td>5</td>
                    <td>3</td>
                    <td>1/375</td>
                    <td>1/600</td>
                    <td>1/1000</td>
                </tr>
            </tbody>
        </table>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = self.scraper._extract_machines_data(soup)

        assert len(result) == 2

        # 1台目
        assert result[0]["model_name"] == "バジリスク絆2"
        assert result[0]["machine_number"] == 101
        assert result[0]["game_count"] == 5000
        assert result[0]["total_difference"] == 1500
        assert result[0]["big_bonus"] == 10
        assert result[0]["regular_bonus"] == 5

        # 2台目
        assert result[1]["model_name"] == "まどマギ叛逆"
        assert result[1]["machine_number"] == 102
        assert result[1]["total_difference"] == -500

    def test_extract_machines_from_fixed_table(self):
        """fixed_get_medals_table クラスからデータを抽出できる"""
        html = """
        <html>
        <body>
        <table class="fixed_get_medals_table">
            <tbody>
                <tr>
                    <td>北斗の拳</td>
                    <td>201</td>
                    <td>8,000</td>
                    <td>+3,000</td>
                    <td>15</td>
                    <td>8</td>
                </tr>
            </tbody>
        </table>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = self.scraper._extract_machines_data(soup)

        assert len(result) == 1
        assert result[0]["model_name"] == "北斗の拳"
        assert result[0]["machine_number"] == 201

    def test_extract_machines_no_table(self):
        """テーブルがない場合は空リストを返す"""
        html = """
        <html>
        <body>
        <div>No data</div>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = self.scraper._extract_machines_data(soup)
        assert result == []

    def test_extract_machines_insufficient_columns(self):
        """カラムが不足している行はスキップされる"""
        html = """
        <html>
        <body>
        <table id="all_data_table">
            <tbody>
                <tr>
                    <td>機種名のみ</td>
                    <td>101</td>
                </tr>
                <tr>
                    <td>完全なデータ</td>
                    <td>102</td>
                    <td>5,000</td>
                    <td>+1,000</td>
                    <td>10</td>
                    <td>5</td>
                </tr>
            </tbody>
        </table>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = self.scraper._extract_machines_data(soup)

        # カラムが不足している行はスキップされ、完全な行のみ取得
        assert len(result) == 1
        assert result[0]["model_name"] == "完全なデータ"


class TestParseMachineRow:
    """_parse_machine_row メソッドのテスト"""

    def setup_method(self):
        self.scraper = AnasloScraper()

    def test_parse_complete_row(self):
        """完全なデータ行をパースできる"""
        html = """
        <tr>
            <td>バジリスク絆2</td>
            <td>101</td>
            <td>5,000</td>
            <td>+1,500</td>
            <td>10</td>
            <td>5</td>
            <td>1/333</td>
            <td>1/500</td>
            <td>1/1000</td>
        </tr>
        """
        soup = BeautifulSoup(html, "html.parser")
        cols = soup.find("tr").find_all("td")
        result = self.scraper._parse_machine_row(cols)

        assert result is not None
        assert result["model_name"] == "バジリスク絆2"
        assert result["machine_number"] == 101
        assert result["game_count"] == 5000
        assert result["total_difference"] == 1500
        assert result["big_bonus"] == 10
        assert result["regular_bonus"] == 5
        assert result["combined_rate"] == "1/333"
        assert result["bb_rate"] == "1/500"
        assert result["rb_rate"] == "1/1000"

    def test_parse_row_minimal_columns(self):
        """最小カラム数（6列）の行をパースできる"""
        html = """
        <tr>
            <td>機種名</td>
            <td>100</td>
            <td>1,000</td>
            <td>-200</td>
            <td>3</td>
            <td>2</td>
        </tr>
        """
        soup = BeautifulSoup(html, "html.parser")
        cols = soup.find("tr").find_all("td")
        result = self.scraper._parse_machine_row(cols)

        assert result is not None
        assert result["model_name"] == "機種名"
        assert result["combined_rate"] is None
        assert result["bb_rate"] is None
        assert result["rb_rate"] is None


class TestScraperInitialization:
    """AnasloScraperの初期化テスト"""

    def test_default_initialization(self):
        """デフォルト設定で初期化できる"""
        scraper = AnasloScraper()
        assert scraper.headless is False
        assert scraper.driver is None

    def test_headless_initialization(self):
        """headlessモードで初期化できる"""
        scraper = AnasloScraper(headless=True)
        assert scraper.headless is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
