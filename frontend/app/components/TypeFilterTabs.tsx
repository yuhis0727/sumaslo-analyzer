"use client";

import { MachineType, typeLabel } from "./Badges";

export type TypeFilter = "all" | MachineType;

const ACTIVE_STYLE: Record<TypeFilter, string> = {
  all: "bg-white text-gray-700 shadow-sm",
  AT: "bg-blue-600 text-white",
  A: "bg-green-600 text-white",
  BT: "bg-purple-600 text-white",
};

/** 機種タイプ絞り込みタブ（全台 / AT機 / Aタイプ / BT機） */
export default function TypeFilterTabs({
  value,
  onChange,
  allLabel = "全台",
}: {
  value: TypeFilter;
  onChange: (t: TypeFilter) => void;
  allLabel?: string;
}) {
  return (
    <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
      {(["all", "AT", "A", "BT"] as const).map((t) => (
        <button
          key={t}
          onClick={() => onChange(t)}
          className={`px-3 py-1 rounded text-xs font-bold transition-colors ${
            value === t ? ACTIVE_STYLE[t] : "text-gray-500 hover:text-gray-700"
          }`}
        >
          {t === "all" ? allLabel : typeLabel(t)}
        </button>
      ))}
    </div>
  );
}
