/**
 * 共通バッジコンポーネント集
 * 勝率・差枚・機種タイプ・順位・曜日の表示を全ページで統一する
 */
import { diffStr } from "../lib/format";

export type MachineType = "AT" | "A" | "BT";

export const TYPE_STYLE: Record<MachineType, string> = {
  AT: "bg-blue-100 text-blue-700",
  A: "bg-green-100 text-green-700",
  BT: "bg-purple-100 text-purple-700",
};

export const typeLabel = (t: MachineType) => (t === "A" ? "Aタイプ" : `${t}機`);

/** 機種タイプチップ（AT機 / Aタイプ / BT機） */
export function TypeBadge({ type, short = false }: { type: MachineType; short?: boolean }) {
  return (
    <span className={`text-xs font-bold px-1.5 py-0.5 rounded shrink-0 ${TYPE_STYLE[type]}`}>
      {short ? type : typeLabel(type)}
    </span>
  );
}

/** 勝率バッジ（80/70/60/50%で段階着色） */
export function WinBadge({ rate, pill = false }: { rate: number; pill?: boolean }) {
  const pct = Math.round(rate * 100);
  const color =
    pct >= 80 ? "bg-green-600 text-white" :
    pct >= 70 ? "bg-green-400 text-white" :
    pct >= 60 ? "bg-green-200 text-green-900" :
    pct >= 50 ? "bg-yellow-100 text-yellow-800" :
    "bg-gray-100 text-gray-500";
  const shape = pill ? "rounded-full text-xs" : "rounded text-sm";
  return (
    <span className={`inline-block px-2 py-0.5 font-bold ${shape} ${color}`}>
      {pct}%
    </span>
  );
}

/** 勝率プログレスバー（機種別分析などバー表示が欲しい箇所用） */
export function WinBar({ rate }: { rate: number }) {
  const pct = Math.round(rate * 100);
  const color =
    pct >= 80 ? "bg-green-500" :
    pct >= 65 ? "bg-green-400" :
    pct >= 50 ? "bg-yellow-400" :
    "bg-gray-300";
  return (
    <div className="flex items-center gap-2">
      <div className="w-24 bg-gray-100 rounded-full h-2">
        <div className={`h-2 rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-sm font-bold ${pct >= 65 ? "text-green-700" : "text-gray-600"}`}>
        {pct}%
      </span>
    </div>
  );
}

/** 差枚テキスト（+3000枚以上は強調） */
export function DiffText({ value, unit = "" }: { value: number; unit?: string }) {
  const color =
    value >= 3000 ? "text-green-700 font-bold" :
    value >= 0 ? "text-green-600 font-medium" :
    "text-red-500";
  return <span className={color}>{diffStr(value)}{unit}</span>;
}

/** 上位3位のメダル風順位バッジ（rank は 1 始まり、4位以降は非表示） */
export function RankBadge({ rank }: { rank: number }) {
  if (rank > 3) return null;
  const cls =
    rank === 1 ? "bg-yellow-400 text-white" :
    rank === 2 ? "bg-gray-300 text-gray-700" :
    "bg-amber-600 text-white";
  return (
    <span className={`text-xs font-bold w-5 h-5 rounded-full flex items-center justify-center shrink-0 ${cls}`}>
      {rank}
    </span>
  );
}

export const DOW_COLOR: Record<string, string> = {
  月: "bg-blue-100 text-blue-800",
  火: "bg-red-100 text-red-800",
  水: "bg-cyan-100 text-cyan-800",
  木: "bg-green-100 text-green-800",
  金: "bg-yellow-100 text-yellow-800",
  土: "bg-purple-100 text-purple-800",
  日: "bg-pink-100 text-pink-800",
};

/** 曜日バッジ */
export function DowBadge({ dow, suffix = "" }: { dow: string; suffix?: string }) {
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${DOW_COLOR[dow] ?? "bg-gray-100"}`}>
      {dow}{suffix}
    </span>
  );
}
