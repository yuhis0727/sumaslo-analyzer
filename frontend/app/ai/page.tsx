"use client";

import { useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import { API } from "../lib/api";

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
      text: "ナナです。マルハン蒲田7の立ち回りを担当します。\n抽選番号を引いた後に「○番引いた。今日のおすすめは？」と聞いてください。\n\n店長ポスト（X）の内容があれば一緒に貼ると精度が上がります。",
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
        <h1 className="text-2xl font-bold text-gray-900">ナナ</h1>
        <span className="text-sm text-gray-400">AI立ち回り支援</span>
        <span className="bg-green-100 text-green-800 text-xs px-2 py-1 rounded-full font-medium">
          Claude Sonnet 稼働中
        </span>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col h-[calc(100dvh-180px)] md:h-[640px]">
        {/* メッセージ一覧 */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm ${
                  m.role === "user"
                    ? "bg-brand text-white rounded-br-none whitespace-pre-wrap leading-relaxed"
                    : "bg-gray-100 text-gray-800 rounded-bl-none"
                }`}
              >
                {m.role === "assistant" && (
                  <div className="text-xs text-gray-400 mb-1.5 font-medium">ナナ</div>
                )}
                {m.role === "user" ? (
                  m.text
                ) : m.text ? (
                  <Markdown
                    components={{
                      h1: ({ children }) => <h1 className="text-base font-bold mt-3 mb-1 text-gray-900 border-b border-gray-300 pb-1">{children}</h1>,
                      h2: ({ children }) => <h2 className="text-sm font-bold mt-3 mb-1 text-gray-800">{children}</h2>,
                      h3: ({ children }) => <h3 className="text-sm font-semibold mt-2 mb-0.5 text-gray-700">{children}</h3>,
                      p: ({ children }) => <p className="my-1 leading-relaxed">{children}</p>,
                      strong: ({ children }) => <strong className="font-bold text-gray-900">{children}</strong>,
                      ul: ({ children }) => <ul className="my-1 ml-4 list-disc space-y-0.5">{children}</ul>,
                      ol: ({ children }) => <ol className="my-1 ml-4 list-decimal space-y-0.5">{children}</ol>,
                      li: ({ children }) => <li className="leading-relaxed">{children}</li>,
                      hr: () => <hr className="my-2 border-gray-300" />,
                      table: ({ children }) => (
                        <div className="overflow-x-auto my-2">
                          <table className="text-xs border-collapse w-full">{children}</table>
                        </div>
                      ),
                      thead: ({ children }) => <thead className="bg-gray-200">{children}</thead>,
                      th: ({ children }) => <th className="border border-gray-300 px-2 py-1 text-left font-semibold">{children}</th>,
                      td: ({ children }) => <td className="border border-gray-300 px-2 py-1">{children}</td>,
                      code: ({ children }) => <code className="bg-gray-200 rounded px-1 font-mono text-xs">{children}</code>,
                    }}
                  >
                    {m.text}
                  </Markdown>
                ) : loading && i === messages.length - 1 ? (
                  <span className="inline-flex gap-1 py-1">
                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                  </span>
                ) : null}
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
              className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30"
              disabled={loading}
            />
            <button
              onClick={() => send(input)}
              disabled={loading || !input.trim()}
              className="bg-brand text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-brand-light disabled:opacity-40 transition-colors"
            >
              送信
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
