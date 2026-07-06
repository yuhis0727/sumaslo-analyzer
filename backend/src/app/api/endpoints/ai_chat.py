"""
AI社員エンドポイント - Claude API連携（ストリーミング）
"""
from __future__ import annotations

import json
import os
from datetime import date

import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()

# ── Claude API クライアント ────────────────────────
def _get_client():
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY が設定されていません")
    from anthropic import AsyncAnthropic
    return AsyncAnthropic(api_key=key)


# ── 静的システムプロンプト ────────────────────────
_SYSTEM_BASE = """あなたの名前はナナ（七）です。マルハン蒲田7店専属のスロット立ち回り支援AIです。
名前の由来は「7の日」から。自己紹介が必要な場面では「ナナです」と名乗ってください。
ユーザーは入場前の数分間に「今日どの台を狙うか」を決めるためにあなたを使います。
以下のルールと本日のデータを元に、具体的な台番と機種名を出して答えてください。

【店舗情報】
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
2. 少数台機種ほど全台系にしやすい。繰り返し全台系になる機種を優先（前回全台系だったからといって次も来るとは限らない）
3. 固定設定6台（別格運用台）が存在する。機種全体が弱くても1台だけ継続的に強い台がある
4. 台番実績の信頼度: Aタイプ >> AT機。Aタイプは台番実績が信頼できる。AT機は全台系の波で動く
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
- 当日夜（17時以降）のポスト → 当日の答え合わせ（結果報告）。翌日への示唆は含まない場合が多い
- ococoichi の夜ポストはほぼ答え合わせ。翌日の参考材料として使う
解釈した内容を回答冒頭で「このポストは〇〇への示唆と判断しました」と明示すること。

【重要原則】
- ニャンギラスはAタイプ優先（BT機は回収傾向・避ける）
- 新台は避ける（導入後数ヶ月は回収傾向）
- ウスイ店長のXポスト示唆があれば最優先（ユーザーが貼る）
- 良番=全台系最良ポジション、悪番=個別実績台
- 曜日別仕掛けをイベント情報と組み合わせて狙い台を絞る

【回答フォーマット】
- 台番と機種名を必ず出す（例: 2026番・スマスロ甲鉄城のカバネリ海門決戦）
- 良番/中番/悪番の戦略分岐を明示する
- 第1候補が取れない場合の第2・第3候補も出す
- 勝率・平均差枚を根拠として使う
- 箇条書きで簡潔に
"""


# ── 今日のデータコンテキスト構築 ────────────────────────
def _build_today_context() -> str:
    from .csv_data import (
        _get_df, _today_event_n, _today_events, _event_days,
        _current_model_map, _model_type, DOW_JP, EVENT_CALENDAR,
        _all_event_timestamps, _N_DAY_SET, _filter_current_model_only,
    )

    df = _get_df()
    today = date.today()
    event_n = _today_event_n()
    latest_date = df["date"].max()
    today_events = _today_events()
    model_map = _current_model_map(df)
    current = set(df[df["date"] == latest_date]["machine_number"])

    lines: list[str] = []
    lines.append(f"=== 本日の状況 ===")
    lines.append(f"日付: {today.isoformat()} ({DOW_JP[today.weekday()]}曜日)")
    lines.append(f"データ最終更新: {latest_date.strftime('%Y-%m-%d')}")

    if today_events:
        lines.append(f"本日のイベント: {', '.join(today_events)}")
    else:
        lines.append("本日の特別イベント: なし")

    if event_n > 0:
        lines.append(f"Nの日: {event_n}の日（{event_n}・{event_n+10}・{event_n+20}日）")
    else:
        lines.append("Nの日: 対象外（10・20・30・31日）")

    # ── Nの日別統計 ──
    if event_n > 0:
        days = _event_days(event_n)
        df_n = df[df["date"].dt.day.isin(days)].copy()
        df_n["mtype"] = df_n["model_name"].map(_model_type)

        lines.append(f"\n--- {event_n}の日 機種タイプ別統計 ---")
        for mt, label in [("A", "Aタイプ"), ("AT", "AT機"), ("BT", "BT機")]:
            sub = df_n[df_n["mtype"] == mt]
            if not sub.empty:
                wr = (sub["total_diff"] > 0).mean()
                avg = int(sub["total_diff"].mean())
                lines.append(f"  {label}: 勝率{wr*100:.0f}% / 平均{avg:+,}枚 / {len(sub)}台日")

        # 台番別TOP20（現機種のデータのみ）
        top = (
            _filter_current_model_only(df_n[df_n["machine_number"].isin(current)])
            .groupby("machine_number")
            .agg(
                win_rate=("total_diff", lambda x: (x > 0).mean()),
                avg_diff=("total_diff", "mean"),
                n=("total_diff", "count"),
            )
            .query("n >= 8")
            .sort_values(["win_rate", "avg_diff"], ascending=False)
            .head(20)
            .reset_index()
        )
        if not top.empty:
            lines.append(f"\n--- {event_n}の日 台番別TOP20（8回以上） ---")
            for _, r in top.iterrows():
                model = model_map.get(int(r["machine_number"]), "不明")
                mtype = _model_type(model)
                lines.append(
                    f"  {int(r['machine_number'])}番 {model[:22]} [{mtype}]"
                    f" 勝率{r['win_rate']*100:.0f}% 平均{int(r['avg_diff']):+,}枚 ({int(r['n'])}回)"
                )

    # ── 固定設定6候補 ──
    try:
        all_ev = _all_event_timestamps()
        df_plain = df[~df["date"].isin(all_ev) & ~df["date"].dt.day.isin(_N_DAY_SET)].copy()
        df_plain["mtype"] = df_plain["model_name"].map(_model_type)

        # 全期間の機種別日平均（現機種のデータのみ）
        df_cur = _filter_current_model_only(df[df["machine_number"].isin(current)])
        model_daily_avg = (
            df_cur.groupby(["date", "model_name"])["total_diff"].mean().reset_index()
            .rename(columns={"total_diff": "model_avg"})
        )
        df_dev = df_cur.merge(model_daily_avg, on=["date", "model_name"])
        df_dev["deviation"] = df_dev["total_diff"] - df_dev["model_avg"]

        dev_stats = (
            df_dev.groupby("machine_number")
            .agg(
                avg_dev=("deviation", "mean"),
                n_days=("deviation", "count"),
                win_vs_model=("deviation", lambda x: (x > 0).mean()),
            )
            .query("n_days >= 30")
            .sort_values("avg_dev", ascending=False)
            .head(8)
            .reset_index()
        )
        if not dev_stats.empty:
            lines.append("\n--- 固定設定6候補（機種平均超えが安定している台） ---")
            for _, r in dev_stats.iterrows():
                model = model_map.get(int(r["machine_number"]), "不明")
                mtype = _model_type(model)
                lines.append(
                    f"  {int(r['machine_number'])}番 {model[:22]} [{mtype}]"
                    f" モデル比+{int(r['avg_dev']):,}枚 勝率{r['win_vs_model']*100:.0f}% ({int(r['n_days'])}日)"
                )
    except Exception:
        pass

    # ── 全台系になりやすい機種（少数台）──
    try:
        latest_models = df[df["date"] == latest_date].groupby("model_name")["machine_number"].count()
        small_models = latest_models[latest_models <= 4].index.tolist()

        if small_models:
            lines.append("\n--- 少数台機種（4台以下・全台系コストが低い） ---")
            for m in small_models[:12]:
                cnt = latest_models[m]
                lines.append(f"  {m} ({cnt}台)")
    except Exception:
        pass

    # ── 示唆情報（ウスイ店長X・ococoichi・LINE）──
    try:
        from .hints import get_today_hints_context
        hints_ctx = get_today_hints_context()
        if hints_ctx:
            lines.append(f"\n=== 本日の示唆情報（最優先） ===\n{hints_ctx}")
    except Exception:
        pass

    return "\n".join(lines)


# ── リクエスト/レスポンス型 ────────────────────────
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


# ── POST /api/ai/chat ────────────────────────
@router.post("/ai/chat")
async def chat(req: ChatRequest):
    """Claude APIによるストリーミングチャット"""
    client = _get_client()

    # 今日のデータを取得してシステムプロンプトに追加
    try:
        today_ctx = _build_today_context()
    except Exception as e:
        today_ctx = f"（データ取得エラー: {e}）"

    system_prompt = _SYSTEM_BASE + "\n\n" + today_ctx

    # 会話履歴を Claude 形式に変換
    messages = [
        {"role": m.role, "content": m.content}
        for m in req.history
        if m.role in ("user", "assistant")
    ]
    messages.append({"role": "user", "content": req.message})

    async def generate():
        try:
            async with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=system_prompt,
                messages=messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield f"data: {json.dumps({'text': text}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
