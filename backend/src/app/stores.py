"""
店舗レジストリ - 複数店舗対応の中核モジュール

店舗ごとの設定（CSVパス・イベントカレンダー・AI用店舗知識・曜日仕掛け）を
一元管理する。新店舗の追加は STORES にエントリを足すだけでよい。

店舗の切替はリクエスト単位: store_middleware が
クエリパラメータ `store`（または X-Store ヘッダ）を読んで
ContextVar に設定し、各エンドポイントは get_store_id() で参照する。
未指定時は DEFAULT_STORE_ID（蒲田7）で従来どおり動作する。
"""
from __future__ import annotations

import os
from contextvars import ContextVar
from pathlib import Path

from starlette.requests import Request
from starlette.responses import JSONResponse

# backend(またはコンテナの/workspace)直下の data ディレクトリ
_BASE_DATA_DIR = Path(__file__).parents[2] / "data"

DEFAULT_STORE_ID = "maruhan_kamata7"

# ── 蒲田7 AI用店舗知識（ai_chat のシステムプロンプトに挿入） ──
_KAMATA7_KNOWLEDGE = """【店舗情報】
マルハン蒲田7店: 715台・2F/3Fスロットフロア
機種タイプ: AT機・Aタイプ(ノーマル)・BT機の3種

【イベント特性（実データ分析値）】
■ 7の日（7日・17日・27日）
  AT機: 平均+134枚 / 勝率50.9%
  Aタイプ: 平均+233枚 / 勝率67.0%
  BT機: 平均+154枚 / 勝率60.0%
  強さ: 27日=7日 > 17日

■ ニャンギラス（1日・11日・21日・31日）
  AT機: 平均+53枚 / 勝率45.0%
  Aタイプ: 平均+284枚 / 勝率64.0%
  BT機: 平均-98枚 / 勝率37.6% → 回収傾向・避ける
  強さ: 1日 > 11日=21日 > 31日
  特徴: 全台系はAT機寄り。悪番でも少数台AT機にチャンスあり

■ ファン感謝デー（2/13-15, 5/22-24）
  5/22はマルハン創業日で特に強い。複数日連続で台番の流れを読みやすい

■ 大田区活性化（月末30日）
  通常日より強め

【店の営業ロジック（データから導いた仮説）】
1. メイン機種は「1/2集中投入」主流。全台系より半数台に設定6集中のパターンが多い
2. 少数台機種ほど全台系にしやすい。繰り返し全台系になる機種を優先
   （前回全台系だったからといって次も来るとは限らない）
3. 固定設定6台（別格運用台）が存在する。機種全体が弱くても1台だけ継続的に強い台がある
4. 台番実績の信頼度: Aタイプ >> AT機。
   Aタイプは台番実績が信頼できる。AT機は全台系の波で動く
5. 配置変更後の旧台番実績は無効

【番号帯別戦略】
良番（上位1/4）: 全台系/1/2本命の最良台を確保。メイン機種の最高実績台が第1候補
中番（中位）: 本命が埋まる前提で少数台全台系機種・固定設定6台を狙う
悪番（下位）: Aタイプ台番実績台・固定設定6台。Aタイプは悪番でも台番実績で狙える

【曜日別共通仕掛け（毎日適用される固定パターン）】
- 月曜: 列全（島の全台に高設定）
- 火曜: 角系（コーナー台に集中）
- 水曜: 末尾（台番の末尾番台、例: X05・X10等）
- 木曜: ランダム（法則なし → データ実績台を信頼）
- 金曜: 列一台以上（各列に最低1台）
- 土曜: 3台並び 末尾起点（島の末尾から3台連続）
- 日曜: 機種1以上・3台以上設置の機種が対象

【示唆ポストの時間帯解釈ルール】
貼られたポストに投稿日時が含まれる場合、以下のように解釈する:
- 前日夜（18時〜翌3時頃）のポスト → 当日への事前示唆
- 当日早朝〜午前中のポスト → 当日への示唆（最も信頼度高い）
- 当日昼〜夕方のポスト → 当日の途中経過・追加示唆の可能性
- 当日夜（17時以降）のポスト → 当日の答え合わせ（結果報告）。
  翌日への示唆は含まない場合が多い
- ococoichi の夜ポストはほぼ答え合わせ。翌日の参考材料として使う
解釈した内容を回答冒頭で「このポストは〇〇への示唆と判断しました」と明示すること。

【情報源の優先順位（上位が下位より優先）】
1. ウスイ店長のXポスト（示唆＝ほぼ答え）
2. ココイチ（@999999Q9Q）のXポスト（店長ポストの解釈補助）
3. LINEオープンチャットのまとめ・ニケ店長のnote等、ユーザーが貼り付けた営業分析テキスト
4. 保有データからの統計予測（フォールバック）
貼り付けられた示唆情報（本日の示唆情報ブロック）は、LINEオープンチャットやニケ店長のnoteの
コピペである場合が多い。これらのテキストには「設定６確定」「全系」「◯台以上確定」といった
具体的な確定情報や、機種別の全系予測ランキングが含まれることがある。
このようなテキスト中の確定情報・具体的な機種名は、統計予測（勝率・平均差枚のみに基づく
固定設定6検出など）よりも優先して直接回答に反映すること。単なる背景情報として要約するだけで
終わらせず、「示唆情報より: ◯◯ 設定６確定」のように出典を明示しながら、狙い台の判断に
実際に組み込むこと。示唆情報が長文の場合でも、確定系の記述を見落とさず全て拾うこと。

【重要原則】
- ニャンギラスはAタイプ優先（BT機は回収傾向・避ける）
- 新台は避ける（導入後数ヶ月は回収傾向）
- ウスイ店長のXポスト示唆があれば最優先（ユーザーが貼る）
- 良番=全台系最良ポジション、悪番=個別実績台
- 曜日別仕掛けをイベント情報と組み合わせて狙い台を絞る
- 「過去の予測実績」がコンテキストに含まれる場合は必ず目を通すこと。平均的中率が低い、
  または振り返りメモに繰り返し出てくる失敗パターン（例:「示唆を見落とした」「固定6候補が
  外れた」）があれば、同じ過ちを繰り返さないよう今回の判断で明確に補正し、その旨を回答に
  一言添えること（例:「前回◯◯を見落として外したので今回は示唆情報を優先しました」）"""

# ── 戸越銀座 AI用店舗知識（データ蓄積中） ──
_TOGOSHI_KNOWLEDGE = """【店舗情報】
BIGディッパー戸越銀座店（2024年12月20日リニューアルオープン、旧フルハウス戸越銀座店）
機種タイプ: AT機・Aタイプ(ノーマル)・BT機の3種

【営業特性（ユーザー確認済み）】
- 1/2仕掛け（機種の半数台に高設定）と全台仕掛け（機種全台に高設定）が毎日ある
- 「どの機種に仕掛けが入るか」を当てることが立ち回りの本質

【情報源】
- 店舗公式Xのポストに仕掛けのヒントが含まれる。ユーザーが貼ったら最優先で解釈し、
  当日の狙い機種の絞り込みに直接使う
- 晒し屋（店長個人・関係者の示唆アカウント）はいない
- LINE公式オープンチャットで、設定が入っていた機種の答え合わせが行われる
- 答え合わせは事後情報: 当日の狙いには使えないが、仕掛け傾向の蓄積・予測検証に使う
- ユーザーが貼ったオープンチャットの内容は仕掛け履歴として扱う

【データ状況（重要）】
この店舗はデータ蓄積を開始したばかりで、機種別の仕掛け傾向・曜日傾向は未解明。
- 確定的な仮説を語らず、統計データ（勝率・平均差枚）と
  ユーザーが貼る示唆情報のみで判断する
- サンプル数が少ない統計を使う場合は、必ず「サンプル◯日分」と明示する
- 蒲田7の営業ロジック（曜日仕掛け・固定設定6等）をこの店舗に流用しない

【番号帯別戦略】
良番（上位1/4）: 全台仕掛け/1/2仕掛け候補機種の最良台を確保
中番（中位）: 本命が埋まる前提で次点候補・少数台機種を狙う
悪番（下位）: 台番実績が信頼しやすいAタイプの高勝率台を優先

【重要原則】
- 新台は避ける（導入後数ヶ月は回収傾向が一般的）
- ユーザーが貼った示唆情報があれば統計予測より優先する
- 毎日仕掛けがある店なので「今日は入っていない」前提を置かない。
  どの機種に入るかの絞り込みに集中する"""

# ── 蒲田7 曜日別仕掛け（simulator用） ──
_KAMATA7_DOW_SHIKAKE: dict[int, tuple[str, str, str]] = {
    0: ("月", "列全", "島の全台に高設定。列ごと狙える番号なら列最良台を最優先。"),
    1: (
        "火", "角系", "コーナー台（島端・角番台）に集中。角番台を台番実績と照合。",
    ),
    2: ("水", "末尾", "台番末尾番台（X05・X10等）に集中。末尾一致台を優先。"),
    3: (
        "木", "ランダム", "法則なし。データ実績台・固定設定6台を純粋に信頼。",
    ),
    4: (
        "金", "列一台以上",
        "各列に最低1台。列内最高実績台を押さえれば当たりやすい。",
    ),
    5: ("土", "3台並び末尾起点", "島の末尾から3台連続。末尾3台セットで狙う。"),
    6: (
        "日", "機種1以上・3台以上対象",
        "3台以上設置機種のうち各機種1台以上。少数台機種は除外。",
    ),
}

STORES: dict[str, dict] = {
    "maruhan_kamata7": {
        "name": "マルハンメガシティ2000蒲田7",
        "short_name": "蒲田7",
        "minrepo_tag_url": (
            "https://min-repo.com/tag/"
            "%e3%83%9e%e3%83%ab%e3%83%8f%e3%83%b3%e3%83%a1%e3%82%ac"
            "%e3%82%b7%e3%83%86%e3%82%a32000%e8%92%b2%e7%94%b07/"
        ),
        # 既存運用との互換のため蒲田7だけ従来のenv名・ファイル名を使う
        "csv_env": "MACHINES_CSV",
        "csv_filename": "machines.csv",
        "hints_env": "HINTS_JSON",
        "hints_filename": "hints.json",
        "predictions_env": "PREDICTIONS_JSON",
        "predictions_filename": "predictions.json",
        "event_calendar": {
            "ニャンギラス": {
                "dates": [
                    "2026-01-01", "2026-01-11", "2026-01-21", "2026-01-31",
                    "2026-02-01", "2026-02-11", "2026-02-21",
                    "2026-03-01", "2026-03-11", "2026-03-21", "2026-03-31",
                    "2026-04-01", "2026-04-11", "2026-04-21",
                    "2026-05-01", "2026-05-11", "2026-05-21",
                    "2026-06-01", "2026-06-11", "2026-06-21",
                    "2026-07-01",
                ],
                "note": "1・11・21・31のつく日。毎月開催のレギュラーイベント。",
            },
            "大田区活性化": {
                "dates": [
                    "2026-01-30", "2026-02-28", "2026-03-30", "2026-04-30",
                    "2026-05-30", "2026-06-13", "2026-06-30",
                ],
                "note": (
                    "月末30日開催。5月で一度終了し6/13に類似イベント再開、"
                    "6/30から元の形式に戻る。"
                ),
            },
            "ファン感謝デー": {
                "dates": [
                    "2026-02-13", "2026-02-14", "2026-02-15",
                    "2026-05-22", "2026-05-23", "2026-05-24",
                ],
                "note": "年2回の複数日開催。5/22はマルハン創業日。",
            },
        },
        "ai_knowledge": _KAMATA7_KNOWLEDGE,
        "dow_shikake": _KAMATA7_DOW_SHIKAKE,
    },
    "bigdipper_togoshiginza": {
        "name": "BIGディッパー戸越銀座",
        "short_name": "戸越銀座",
        "minrepo_tag_url": (
            "https://min-repo.com/tag/"
            "%E3%83%93%E3%83%83%E3%82%AF%E3%83%87%E3%82%A3%E3%83%83"
            "%E3%83%91%E3%83%BC%E6%88%B8%E8%B6%8A%E9%8A%80%E5%BA%A7%E5%BA%97/"
        ),
        "csv_env": "MACHINES_CSV_BIGDIPPER_TOGOSHIGINZA",
        "csv_filename": "machines_bigdipper_togoshiginza.csv",
        "hints_env": "HINTS_JSON_BIGDIPPER_TOGOSHIGINZA",
        "hints_filename": "hints_bigdipper_togoshiginza.json",
        "predictions_env": "PREDICTIONS_JSON_BIGDIPPER_TOGOSHIGINZA",
        "predictions_filename": "predictions_bigdipper_togoshiginza.json",
        # イベント傾向は未解明。判明したら追記する
        "event_calendar": {},
        "ai_knowledge": _TOGOSHI_KNOWLEDGE,
        "dow_shikake": None,
    },
}

current_store_id: ContextVar[str] = ContextVar(
    "current_store_id", default=DEFAULT_STORE_ID
)


def get_store_id() -> str:
    """現在のリクエストの店舗ID（リクエスト外ではデフォルト店舗）"""
    return current_store_id.get()


def get_store(store_id: str | None = None) -> dict:
    return STORES[store_id or get_store_id()]


def _data_path(env_key: str, filename: str) -> str:
    return os.environ.get(env_key, str(_BASE_DATA_DIR / filename))


def csv_path(store_id: str | None = None) -> str:
    s = get_store(store_id)
    return _data_path(s["csv_env"], s["csv_filename"])


def hints_path(store_id: str | None = None) -> str:
    s = get_store(store_id)
    return _data_path(s["hints_env"], s["hints_filename"])


def predictions_path(store_id: str | None = None) -> str:
    s = get_store(store_id)
    return _data_path(s["predictions_env"], s["predictions_filename"])


def event_calendar(store_id: str | None = None) -> dict[str, dict]:
    return get_store(store_id)["event_calendar"]


def _has_data(store_id: str) -> bool:
    p = Path(csv_path(store_id))
    return p.is_file() and p.stat().st_size > 0


def stores_meta() -> list[dict]:
    """フロントの店舗切替UI用メタ情報"""
    return [
        {
            "id": sid,
            "name": s["name"],
            "short_name": s["short_name"],
            "has_data": _has_data(sid),
            "is_default": sid == DEFAULT_STORE_ID,
        }
        for sid, s in STORES.items()
    ]


async def store_middleware(request: Request, call_next):
    """`?store=` / X-Store ヘッダから店舗を解決して ContextVar に設定する"""
    sid = (
        request.query_params.get("store")
        or request.headers.get("X-Store")
        or DEFAULT_STORE_ID
    )
    if sid not in STORES:
        return JSONResponse(
            status_code=404,
            content={"detail": f"店舗 '{sid}' は登録されていません"},
        )
    token = current_store_id.set(sid)
    try:
        return await call_next(request)
    finally:
        current_store_id.reset(token)
