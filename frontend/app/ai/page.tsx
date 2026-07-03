"use client";

import { useState } from "react";
import axios from "axios";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

type Message = {
  role: "user" | "assistant";
  text: string;
};

const SUGGESTIONS = [
  "今日のおすすめ台は？",
  "7の日で一番勝率高い台番は？",
  "2026番の最近の成績は？",
  "全台系になりやすい機種は？",
];

export default function AIPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      text: "マルハン蒲田7の分析AIです。台番・Nの日の勝率・おすすめ台などについて聞いてください。\n\n※ Claude APIキー設定後に本格稼働します（現在はデモ応答）",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const send = async (text: string) => {
    if (!text.trim() || loading) return;
    const userMsg: Message = { role: "user", text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      // コンテキスト取得
      const ctx = await axios.get(`${API}/api/data/ai-context?question=${encodeURIComponent(text)}`);
      const context = ctx.data;

      // TODO: Claude API呼び出し（APIキー設定後に実装）
      // 現在はコンテキストベースのルールベース応答
      const reply = buildMockReply(text, context);

      setMessages((prev) => [...prev, { role: "assistant", text: reply }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "APIエラーが発生しました。バックエンドの接続を確認してください。" },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold text-gray-900">AI社員</h1>
        <span className="bg-yellow-100 text-yellow-800 text-xs px-2 py-1 rounded-full font-medium">
          β版・デモ応答中
        </span>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col h-[600px]">
        {/* メッセージ一覧 */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {messages.map((m, i) => (
            <div
              key={i}
              className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap leading-relaxed ${
                  m.role === "user"
                    ? "bg-[#1A3A5C] text-white rounded-br-none"
                    : "bg-gray-100 text-gray-800 rounded-bl-none"
                }`}
              >
                {m.role === "assistant" && (
                  <div className="text-xs text-gray-400 mb-1 font-medium">🤖 AI社員</div>
                )}
                {m.text}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 rounded-2xl rounded-bl-none px-4 py-3">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* サジェスト */}
        <div className="px-5 pb-2 flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => send(s)}
              className="bg-gray-50 border border-gray-200 text-gray-700 text-xs px-3 py-1 rounded-full hover:bg-blue-50 hover:border-blue-300 transition-colors"
            >
              {s}
            </button>
          ))}
        </div>

        {/* 入力欄 */}
        <div className="p-4 border-t border-gray-100">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send(input)}
              placeholder="質問を入力（例: 7の日で一番強い台番は？）"
              className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1A3A5C]/30"
            />
            <button
              onClick={() => send(input)}
              disabled={loading || !input.trim()}
              className="bg-[#1A3A5C] text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-[#2a5a8c] disabled:opacity-40 transition-colors"
            >
              送信
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function buildMockReply(question: string, ctx: Record<string, unknown>): string {
  const today = ctx.today as string;
  const dow = ctx.day_of_week as string;
  const eventN = ctx.event_n as number | null;
  const picks = ctx.top_picks as Array<{ num: number; model: string; win: string; avg: string }> | undefined;

  if (question.includes("おすすめ") || question.includes("今日")) {
    if (!eventN) {
      return `今日（${today} ${dow}曜）は通常日です。Nの日ではないため、特定のイベントパターンには当てはまりません。`;
    }
    const list = picks?.slice(0, 5).map((p, i) =>
      `${i + 1}. **${p.num}番**（${p.model.slice(0, 15)}）勝率${p.win} 平均${p.avg}`
    ).join("\n") ?? "データ取得中";
    return `今日は${dow}曜・${eventN}の日です。\n\nおすすめ台TOP5:\n${list}\n\nデータは ${ctx.latest_data_date} まで反映済みです。`;
  }

  if (question.includes("全台系")) {
    return `全台系の判定は「実際の稼働台数が7台の機種」が基準の一つです。\n当日のみんレポで各機種の稼働台数を確認し、7台稼働機種に注目してください。`;
  }

  if (question.includes("勝率")) {
    if (eventN && picks && picks.length > 0) {
      const top = picks[0];
      return `${eventN}の日の最高勝率台は **${top.num}番**（${top.model.slice(0, 20)}）で勝率${top.win}、平均${top.avg}です。`;
    }
  }

  return `「${question}」について分析します。\n\nClaude APIキーを設定すると、より詳細な分析・推論が可能になります。現在はデモ応答中です。\n\n台番分析ページや機種別ページで直接データを確認することをお勧めします。`;
}
