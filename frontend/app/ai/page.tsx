"use client";

import { useEffect, useRef, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

type Message = {
  role: "user" | "assistant";
  text: string;
};

const SUGGESTIONS = [
  "今日のおすすめ台は？",
  "良番（上位10番）で何を狙う？",
  "悪番でも狙える台は？",
  "今日の固定設定6候補は？",
];

export default function AIPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      text: "マルハン蒲田7の立ち回り支援AIです。\n抽選番号を引いた後に「○番引いた。今日のおすすめは？」のように聞いてください。\n\n店長ポスト（X）の内容があれば一緒に貼ると精度が上がります。",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async (text: string) => {
    if (!text.trim() || loading) return;

    const userMsg: Message = { role: "user", text };
    const history = messages
      .slice(1)
      .map(m => ({ role: m.role, content: m.text }));

    setMessages(prev => [...prev, userMsg, { role: "assistant", text: "" }]);
    setInput("");
    setLoading(true);

    try {
      const resp = await fetch(`${API}/api/ai/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, history }),
      });

      if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`);

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6).trim();
          if (payload === "[DONE]") break;
          try {
            const { text: chunk, error } = JSON.parse(payload);
            if (error) throw new Error(error);
            if (chunk) {
              setMessages(prev => {
                const next = [...prev];
                next[next.length - 1] = {
                  role: "assistant",
                  text: next[next.length - 1].text + chunk,
                };
                return next;
              });
            }
          } catch {
            // JSON parse error — skip malformed chunk
          }
        }
      }
    } catch (e) {
      setMessages(prev => {
        const next = [...prev];
        next[next.length - 1] = {
          role: "assistant",
          text: `エラー: ${e instanceof Error ? e.message : "通信エラー"}`,
        };
        return next;
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold text-gray-900">AI社員</h1>
        <span className="bg-green-100 text-green-800 text-xs px-2 py-1 rounded-full font-medium">
          Claude Sonnet 稼働中
        </span>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col h-[640px]">
        {/* メッセージ一覧 */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap leading-relaxed ${
                  m.role === "user"
                    ? "bg-[#1A3A5C] text-white rounded-br-none"
                    : "bg-gray-100 text-gray-800 rounded-bl-none"
                }`}
              >
                {m.role === "assistant" && (
                  <div className="text-xs text-gray-400 mb-1.5 font-medium">AI社員</div>
                )}
                {m.text || (loading && i === messages.length - 1 ? (
                  <span className="inline-flex gap-1 py-1">
                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                  </span>
                ) : "")}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        {/* サジェスト */}
        <div className="px-5 pb-2 flex flex-wrap gap-2">
          {SUGGESTIONS.map(s => (
            <button
              key={s}
              onClick={() => send(s)}
              disabled={loading}
              className="bg-gray-50 border border-gray-200 text-gray-700 text-xs px-3 py-1 rounded-full hover:bg-blue-50 hover:border-blue-300 transition-colors disabled:opacity-40"
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
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === "Enter" && !e.shiftKey && send(input)}
              placeholder="例: 35番引いた。今日7の日で何を狙う？"
              className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1A3A5C]/30"
              disabled={loading}
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
