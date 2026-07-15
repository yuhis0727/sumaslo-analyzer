"""
イベント分析APIのテスト。
テスト用ミニCSVをtmpfileに作成し、FastAPIのTestClientで各エンドポイントを叩く。
"""
from __future__ import annotations

import csv
import os
import sys

import pytest
from fastapi.testclient import TestClient

src_path = os.path.join(os.path.dirname(__file__), "..", "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)


# テスト用CSVを作成してから app を import する
@pytest.fixture(scope="module")
def csv_file(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("data")
    path = tmp / "machines.csv"

    # ニャンギラス日: 2026-01-11, 2026-01-21
    # 大田区活性化: 2026-01-30
    # ファン感謝デー: 2026-02-13, 2026-02-14
    # 通常日: 2026-01-15
    dates_machines = [
        # date, machine_number, model_name, total_diff, game_count
        ("2026-01-11", 1001, "機種A", 3000, 500),
        ("2026-01-11", 1002, "機種A", 2000, 480),
        ("2026-01-11", 1003, "機種B", -500, 300),
        ("2026-01-11", 1004, "機種B", 1000, 400),
        ("2026-01-21", 1001, "機種A", 2500, 490),
        ("2026-01-21", 1002, "機種A", 1800, 460),
        ("2026-01-21", 1003, "機種B", 800, 350),
        ("2026-01-21", 1004, "機種B", -200, 300),
        ("2026-01-15", 1001, "機種A", -1000, 600),
        ("2026-01-15", 1002, "機種A", -800, 580),
        ("2026-01-15", 1003, "機種B", 500, 400),
        ("2026-01-15", 1004, "機種B", -300, 350),
        ("2026-01-30", 1001, "機種A", 4000, 600),
        ("2026-01-30", 1002, "機種A", 3500, 550),
        ("2026-01-30", 1003, "機種B", -100, 300),
        ("2026-01-30", 1004, "機種B", 200, 320),
        ("2026-02-13", 1001, "機種A", 5000, 700),
        ("2026-02-13", 1002, "機種A", 4000, 680),
        ("2026-02-13", 1003, "機種B", 3000, 500),
        ("2026-02-13", 1004, "機種B", 2000, 450),
        ("2026-02-14", 1001, "機種A", 4500, 690),
        ("2026-02-14", 1002, "機種A", 3800, 660),
        ("2026-02-14", 1003, "機種B", 2500, 480),
        ("2026-02-14", 1004, "機種B", 1500, 420),
    ]

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["date", "machine_number", "model_name", "total_diff", "game_count", "rate"]
        )
        for d, num, model, diff, game in dates_machines:
            rate = round(diff / game, 3) if game else 0
            writer.writerow([d, num, model, diff, game, rate])

    return str(path)


@pytest.fixture(scope="module")
def client(csv_file):
    os.environ["MACHINES_CSV"] = csv_file
    # lru_cache をクリアしてから import
    import importlib

    import app.api.endpoints.csv_data as mod
    mod._load_df.cache_clear()
    importlib.reload(mod)

    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(mod.router, prefix="/api")
    return TestClient(app)


# ── /api/data/events ──────────────────────────────
class TestEventsEndpoint:
    def test_returns_all_three_events(self, client):
        res = client.get("/api/data/events")
        assert res.status_code == 200
        names = [e["event_name"] for e in res.json()]
        assert "ニャンギラス" in names
        assert "大田区活性化" in names
        assert "ファン感謝デー" in names

    def test_dates_in_data_count(self, client):
        res = client.get("/api/data/events")
        events = {e["event_name"]: e for e in res.json()}
        # テストCSVには 1/11, 1/21 の2日のみニャンギラス日が存在
        assert events["ニャンギラス"]["dates_in_data"] == 2
        # 大田区: 1/30 の1日
        assert events["大田区活性化"]["dates_in_data"] == 1
        # ファン感謝デー: 2/13, 2/14 の2日
        assert events["ファン感謝デー"]["dates_in_data"] == 2

    def test_note_included(self, client):
        res = client.get("/api/data/events")
        for e in res.json():
            assert "note" in e and len(e["note"]) > 0


# ── /api/data/event-analysis ──────────────────────
class TestEventAnalysis:
    def test_nyangilath_dates_summary(self, client):
        res = client.get("/api/data/event-analysis?event=ニャンギラス")
        assert res.status_code == 200
        data = res.json()
        assert data["event_name"] == "ニャンギラス"
        # 2日分のサマリー
        assert len(data["dates_summary"]) == 2

    def test_dates_are_sorted_asc(self, client):
        res = client.get("/api/data/event-analysis?event=ニャンギラス")
        dates = [d["date"] for d in res.json()["dates_summary"]]
        assert dates == sorted(dates)

    def test_positive_rate_range(self, client):
        res = client.get("/api/data/event-analysis?event=ニャンギラス")
        for d in res.json()["dates_summary"]:
            assert 0.0 <= d["positive_rate"] <= 1.0

    def test_top_models_returned(self, client):
        res = client.get("/api/data/event-analysis?event=ニャンギラス")
        data = res.json()
        assert len(data["top_models"]) >= 1
        for m in data["top_models"]:
            assert "model_name" in m
            assert "win_rate" in m
            assert "avg_diff" in m

    def test_top_machines_returned(self, client):
        res = client.get("/api/data/event-analysis?event=ニャンギラス")
        data = res.json()
        assert len(data["top_machines"]) >= 1
        for m in data["top_machines"]:
            assert "machine_number" in m
            assert "win_rate" in m

    def test_fansanshaday_has_highest_avg(self, client):
        """ファン感謝デーは全日プラスなので avg_diff が正になるはず"""
        res = client.get("/api/data/event-analysis?event=ファン感謝デー")
        assert res.status_code == 200
        data = res.json()
        for d in data["dates_summary"]:
            assert d["avg_diff"] > 0

    def test_unknown_event_returns_404(self, client):
        res = client.get("/api/data/event-analysis?event=存在しないイベント")
        assert res.status_code == 404

    def test_overall_avg_diff_present(self, client):
        res = client.get("/api/data/event-analysis?event=大田区活性化")
        assert "overall_avg_diff" in res.json()

    def test_top_model_sort_order(self, client):
        """機種Aは機種Bより勝率が高いはずなので先頭に来る"""
        res = client.get("/api/data/event-analysis?event=ニャンギラス")
        models = res.json()["top_models"]
        assert models[0]["model_name"] == "機種A"
        assert models[0]["win_rate"] >= models[-1]["win_rate"]
