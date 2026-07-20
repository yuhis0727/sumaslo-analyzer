"""
AI社員エンドポイント - Claude API連携（ストリーミング）
"""
from __future__ import annotations

import json
import os
from datetime import date

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ... import stores

router = APIRouter()

# ── Claude API クライアント ────────────────────────
def _get_client():
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise HTTPException(
            status_code=500, detail="ANTHROPIC_API_KEY が設定されていません"
        )
    from anthropic import AsyncAnthropic
    return AsyncAnthropic(api_key=key)


# ── 静的システムプロンプト ────────────────────────
# 店舗固有の知識（イベント特性・営業ロジック等）は stores.py の
# ai_knowledge に持たせ、共通部分とリクエスト時に合成する。
_SYSTEM_HEAD = """あなたの名前はナナ（七）です。
「{store_name}」専属のスロット立ち回り支援AIです。
名前の由来は「7の日」から。自己紹介が必要な場面では「ナナです」と名乗ってください。
ユーザーは入場前の数分間に「今日どの台を狙うか」を決めるためにあなたを使います。
以下のルールと本日のデータを元に、具体的な台番と機種名を出して答えてください。"""

_SYSTEM_TAIL = """【回答フォーマット】
- 台番と機種名を必ず出す（例: 2026番・スマスロ甲鉄城のカバネリ海門決戦）
- 良番/中番/悪番の戦略分岐を明示する
- 第1候補が取れない場合の第2・第3候補も出す
- 勝率・平均差枚を根拠として使う
- 箇条書きで簡潔に

【機械可読な推奨リスト（システム用・必須）】
具体的な台番を1つでも推奨する回答では、回答本文の一番最後に、人間には見せない
機械可読ブロックとして以下の形式で推奨台リストを付与すること。本文中で明確に
「狙い台」として挙げた台番のみを含める。世間話・質問への確認・エラー説明など、
具体的な台番を1つも推奨しない回答では省略してよい。

===PICKS===
[{"machine_number": 2026, "model_name": "カバネリ海門決戦", "reason": "固定設定6候補"}]
===END_PICKS===

- JSON配列を1行で出力し、前後に余計な文章・コードフェンスを付けない
- machine_numberは数値、model_name/reasonは短い文字列（reasonは20文字以内目安）
- 本文中の説明は普段通り自然に書き、このブロックは末尾に追加するだけでよい
"""


def _system_base() -> str:
    """現在の店舗に合わせたシステムプロンプト（本日データを除く静的部分）"""
    store = stores.get_store()
    return "\n\n".join([
        _SYSTEM_HEAD.format(store_name=store["name"]),
        store["ai_knowledge"],
        _SYSTEM_TAIL,
    ])


# ── 今日のデータコンテキスト構築 ────────────────────────
def _build_today_context() -> str:
    from .csv_data import (
        _N_DAY_SET,
        DOW_JP,
        _all_event_timestamps,
        _current_model_map,
        _event_days,
        _filter_current_model_only,
        _get_df,
        _model_type,
        _today_event_n,
        _today_events,
    )

    df = _get_df()
    today = date.today()
    event_n = _today_event_n()
    latest_date = df["date"].max()
    today_events = _today_events()
    model_map = _current_model_map(df)
    current = set(df[df["date"] == latest_date]["machine_number"])

    lines: list[str] = []
    lines.append("=== 本日の状況 ===")
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
                lines.append(
                    f"  {label}: 勝率{wr*100:.0f}% / 平均{avg:+,}枚 / {len(sub)}台日"
                )

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
                    f" 勝率{r['win_rate']*100:.0f}%"
                    f" 平均{int(r['avg_diff']):+,}枚 ({int(r['n'])}回)"
                )

    # ── 固定設定6候補 ──
    try:
        all_ev = _all_event_timestamps()
        df_plain = df[
            ~df["date"].isin(all_ev) & ~df["date"].dt.day.isin(_N_DAY_SET)
        ].copy()
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
                    f" モデル比+{int(r['avg_dev']):,}枚"
                    f" 勝率{r['win_vs_model']*100:.0f}% ({int(r['n_days'])}日)"
                )
    except Exception:
        pass

    # ── 全台系になりやすい機種（少数台）──
    try:
        latest_counts = df[df["date"] == latest_date]
        latest_models = latest_counts.groupby("model_name")["machine_number"].count()
        small_models = latest_models[latest_models <= 4].index.tolist()

        if small_models:
            lines.append("\n--- 少数台機種（4台以下・全台系コストが低い） ---")
            for m in small_models[:12]:
                cnt = latest_models[m]
                lines.append(f"  {m} ({cnt}台)")
    except Exception:
        pass

    # ── 過去の予測実績（検証ループ）──
    try:
        from .predictions import get_recent_summary
        summary = get_recent_summary(limit=10)
        n_judged = summary["judged_entries"]
        if n_judged > 0:
            lines.append(f"\n=== 過去の予測実績（直近{n_judged}件・的中判定済み） ===")
            if summary["overall_hit_rate"] is not None:
                lines.append(f"平均的中率: {summary['overall_hit_rate']*100:.0f}%")
            if summary["recent_notes"]:
                lines.append("振り返りメモ（ユーザーが記録した外れ理由等）:")
                for n in summary["recent_notes"]:
                    hr = (
                        f"{n['hit_rate']*100:.0f}%的中"
                        if n["hit_rate"] is not None else "判定待ち"
                    )
                    tier = n.get("tier") or "-"
                    lines.append(f"  {n['date']}（{tier}・{hr}）: {n['note']}")
    except Exception:
        pass

    # ── 示唆テキスト（ウスイ店長X・ococoichi・LINE）──
    try:
        from .hints import get_today_hints_context
        hints_text, _ = get_today_hints_context()
        if hints_text:
            lines.append(f"\n=== 本日の示唆情報（最優先） ===\n{hints_text}")
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

    system_prompt = _system_base() + "\n\n" + today_ctx

    # 会話履歴を Claude 形式に変換
    messages = [
        {"role": m.role, "content": m.content}
        for m in req.history
        if m.role in ("user", "assistant")
    ]

    # 示唆画像を会話の先頭に注入。Claude APIはステートレスなため、
    # 会話が続いても画像を参照できるよう履歴の有無にかかわらず毎ターン含める。
    try:
        from .hints import get_today_hints_context
        _, image_blocks = get_today_hints_context()
        if image_blocks:
            img_content: list[dict] = []
            for blk in image_blocks:
                img_content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": blk["media_type"],
                        "data": blk["data"],
                    },
                })
                img_content.append({"type": "text", "text": f"↑ {blk['label']}"})
            img_content.append({
                "type": "text",
                "text": (
                    "上記は本日の示唆画像です。内容をすべて読み取り、"
                    "今日の狙い台判断に最優先で使ってください。"
                ),
            })
            messages.insert(0, {"role": "user", "content": img_content})
            ack_text = (
                "示唆画像を確認しました。内容を読み取り、今日の立ち回りの参考にします。"
            )
            messages.insert(1, {"role": "assistant", "content": ack_text})
    except Exception:
        pass

    messages.append({"role": "user", "content": req.message})

    async def generate():
        try:
            async with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=4096,
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
