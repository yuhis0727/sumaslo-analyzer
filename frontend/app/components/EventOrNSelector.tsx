"use client";

export type FilterMode = "n" | "event" | "plain" | "all";
export const EVENT_NAMES = ["ニャンギラス", "大田区活性化", "ファン感謝デー"] as const;
export type EventName = typeof EVENT_NAMES[number];

type Props = {
  mode: FilterMode;
  n: number;
  event: EventName;
  onModeChange: (m: FilterMode) => void;
  onNChange: (n: number) => void;
  onEventChange: (e: EventName) => void;
};

const LABEL: Record<FilterMode, string> = {
  n: "Nの日",
  event: "イベント",
  plain: "平常日",
  all: "全期間",
};

export default function EventOrNSelector({ mode, n, event, onModeChange, onNChange, onEventChange }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      {/* モード切替 */}
      <div className="flex rounded-lg border border-gray-300 overflow-hidden text-sm font-medium">
        {(["n", "event", "plain", "all"] as FilterMode[]).map((m) => (
          <button
            key={m}
            onClick={() => onModeChange(m)}
            className={`px-3 py-1.5 transition-colors ${
              mode === m
                ? m === "plain"
                  ? "bg-gray-600 text-white"
                  : m === "all"
                  ? "bg-slate-500 text-white"
                  : "bg-[#1A3A5C] text-white"
                : "bg-white text-gray-600 hover:bg-gray-50"
            }`}
          >
            {LABEL[m]}
          </button>
        ))}
      </div>

      {/* N選択 */}
      {mode === "n" && (
        <div className="flex gap-1">
          {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((v) => (
            <button
              key={v}
              onClick={() => onNChange(v)}
              className={`w-8 h-8 rounded text-sm font-bold transition-colors ${
                n === v
                  ? "bg-[#1A3A5C] text-white"
                  : "bg-white border border-gray-300 text-gray-700 hover:bg-gray-50"
              }`}
            >
              {v}
            </button>
          ))}
        </div>
      )}

      {/* イベント選択 */}
      {mode === "event" && (
        <div className="flex gap-1 flex-wrap">
          {EVENT_NAMES.map((e) => (
            <button
              key={e}
              onClick={() => onEventChange(e)}
              className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                event === e
                  ? "bg-amber-500 text-white"
                  : "bg-white border border-gray-300 text-gray-700 hover:bg-gray-50"
              }`}
            >
              {e}
            </button>
          ))}
        </div>
      )}

      {/* 平常日: 説明テキスト */}
      {mode === "plain" && (
        <span className="text-xs text-gray-400">Nの日・イベント日を除いた日（10日・20日・非イベント30/31日）</span>
      )}

      {/* 全期間: 説明テキスト */}
      {mode === "all" && (
        <span className="text-xs text-gray-400">全日程合算（新台など日数が少ない台の確認に）</span>
      )}
    </div>
  );
}
