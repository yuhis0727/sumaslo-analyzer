"use client";

export type FilterMode = "n" | "event";
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

export default function EventOrNSelector({ mode, n, event, onModeChange, onNChange, onEventChange }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      {/* モード切替 */}
      <div className="flex rounded-lg border border-gray-300 overflow-hidden text-sm font-medium">
        {(["n", "event"] as FilterMode[]).map((m) => (
          <button
            key={m}
            onClick={() => onModeChange(m)}
            className={`px-3 py-1.5 transition-colors ${
              mode === m
                ? "bg-[#1A3A5C] text-white"
                : "bg-white text-gray-600 hover:bg-gray-50"
            }`}
          >
            {m === "n" ? "Nの日" : "イベント"}
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
    </div>
  );
}
