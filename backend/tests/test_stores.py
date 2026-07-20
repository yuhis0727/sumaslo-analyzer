"""
複数店舗対応のテスト。
店舗別のミニCSVを2つ作り、`?store=` パラメータでデータ・イベント・
示唆保存先が店舗ごとに切り替わることを確認する。
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


def _write_csv(path, rows) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["date", "machine_number", "model_name", "total_diff", "game_count", "rate"]
        )
        writer.writerows(rows)


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("stores")
    kamata_csv = tmp / "kamata.csv"
    togoshi_csv = tmp / "togoshi.csv"
    _write_csv(kamata_csv, [
        ("2026-01-11", 1001, "蒲田機種A", 3000, 500, 6.0),
        ("2026-01-11", 1002, "蒲田機種A", 2000, 480, 4.2),
        ("2026-01-12", 1001, "蒲田機種A", -500, 400, -1.3),
        ("2026-01-12", 1002, "蒲田機種A", 800, 300, 2.7),
    ])
    _write_csv(togoshi_csv, [
        ("2026-01-11", 2001, "戸越機種B", 1000, 300, 3.3),
        ("2026-01-11", 2002, "戸越機種B", -200, 250, -0.8),
        ("2026-01-12", 2001, "戸越機種B", 800, 250, 3.2),
        ("2026-01-12", 2002, "戸越機種B", 300, 200, 1.5),
    ])
    os.environ["MACHINES_CSV"] = str(kamata_csv)
    os.environ["MACHINES_CSV_BIGDIPPER_TOGOSHIGINZA"] = str(togoshi_csv)
    os.environ["HINTS_JSON"] = str(tmp / "hints.json")
    os.environ["HINTS_JSON_BIGDIPPER_TOGOSHIGINZA"] = str(
        tmp / "hints_togoshi.json"
    )

    import app.api.endpoints.csv_data as csv_mod
    import app.api.endpoints.hints as hints_mod
    from app.stores import store_middleware
    csv_mod._load_df.cache_clear()

    from fastapi import FastAPI
    app = FastAPI()
    app.middleware("http")(store_middleware)
    app.include_router(csv_mod.router, prefix="/api")
    app.include_router(hints_mod.router, prefix="/api")
    return TestClient(app)


class TestStoreSwitching:
    def test_default_store_is_kamata(self, client):
        res = client.get("/api/data/machine/1001")
        assert res.status_code == 200
        assert res.json()["model_name"] == "蒲田機種A"

    def test_togoshi_store_param(self, client):
        res = client.get(
            "/api/data/machine/2001", params={"store": "bigdipper_togoshiginza"}
        )
        assert res.status_code == 200
        assert res.json()["model_name"] == "戸越機種B"

    def test_kamata_machine_not_in_togoshi(self, client):
        res = client.get(
            "/api/data/machine/1001", params={"store": "bigdipper_togoshiginza"}
        )
        assert res.status_code == 404

    def test_x_store_header(self, client):
        res = client.get(
            "/api/data/machine/2001",
            headers={"X-Store": "bigdipper_togoshiginza"},
        )
        assert res.status_code == 200

    def test_unknown_store_returns_404(self, client):
        res = client.get("/api/data/recent", params={"store": "unknown_store"})
        assert res.status_code == 404
        assert "登録されていません" in res.json()["detail"]

    def test_missing_csv_returns_404(self, client, monkeypatch, tmp_path):
        monkeypatch.setenv(
            "MACHINES_CSV_BIGDIPPER_TOGOSHIGINZA", str(tmp_path / "nai.csv")
        )
        res = client.get(
            "/api/data/recent", params={"store": "bigdipper_togoshiginza"}
        )
        assert res.status_code == 404
        assert "データがまだありません" in res.json()["detail"]


class TestStoresEndpoint:
    def test_lists_both_stores(self, client):
        res = client.get("/api/stores")
        assert res.status_code == 200
        ids = [s["id"] for s in res.json()]
        assert "maruhan_kamata7" in ids
        assert "bigdipper_togoshiginza" in ids

    def test_default_flag(self, client):
        res = client.get("/api/stores")
        defaults = [s["id"] for s in res.json() if s["is_default"]]
        assert defaults == ["maruhan_kamata7"]


class TestPerStoreEventCalendar:
    def test_kamata_has_events(self, client):
        res = client.get("/api/data/events")
        assert res.status_code == 200
        assert len(res.json()) >= 3

    def test_togoshi_has_no_events_yet(self, client):
        res = client.get(
            "/api/data/events", params={"store": "bigdipper_togoshiginza"}
        )
        assert res.status_code == 200
        assert res.json() == []


class TestPerStoreHints:
    def test_hints_saved_separately(self, client):
        client.post("/api/hints/today", json={"store_post": "蒲田の示唆"})
        client.post(
            "/api/hints/today",
            params={"store": "bigdipper_togoshiginza"},
            json={"store_post": "戸越の示唆"},
        )

        kamata = client.get("/api/hints/today").json()
        togoshi = client.get(
            "/api/hints/today", params={"store": "bigdipper_togoshiginza"}
        ).json()
        assert kamata["store_post"] == "蒲田の示唆"
        assert togoshi["store_post"] == "戸越の示唆"
