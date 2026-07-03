"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import EventOrNSelector, { FilterMode, EventName } from "../components/EventOrNSelector";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

type Machine = {
  machine_number: number;
  model_name: string;
  win_rate: number;
  avg_diff: number;
  total_diff: number;
  n_days: number;
};

function WinBadge({ rate }: { rate: number }) {
  const pct = Math.round(rate * 100);
  const color =
    pct >= 80 ? "bg-green-600 text-white" :
    pct >= 70 ? "bg-green-400 text-white" :
    pct >= 60 ? "bg-green-200 text-green-900" :
    pct >= 50 ? "bg-yellow-100 text-yellow-800" :
    "bg-gray-100 text-gray-500";
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-sm font-bold ${color}`}>
      {pct}%
    </span>
  );
}

export default function MachinesPage() {
  const [mode, setMode] = useState<FilterMode>("n");
  const [n, setN] = useState(7);
  const [event, setEvent] = useState<EventName>("ニャンギラス");
  const [minDays, setMinDays] = useState(8);
  const [machines, setMachines] = useState<Machine[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");

  const buildParams = (m: FilterMode, nVal: number, ev: EventName, min: number) => {
    const p = new URLSearchParams({ min_days: String(min), limit: "300" });
    if (m === "n") p.set("n", String(nVal));
    else p.set("event", ev);
    return p.toString();
  };

  const fetch = (m: FilterMode, nVal: number, ev: EventName, min: number) => {
    setLoading(true);
    axios
      .get<Machine[]>(`${API}/api/data/machines?${buildParams(m, nVal, ev, min)}`)
      .then((r) => setMachines(r.data))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetch(mode, n, event, minDays); }, []);

  const handleMode = (m: FilterMode) => { setMode(m); fetch(m, n, event, minDays); };
  const handleN = (v: number) => { setN(v); fetch(mode, v, event, minDays); };
  const handleEvent = (e: EventName) => { setEvent(e); fetch(mode, n, e, minDays); };
  const handleMinDays = (v: number) => { setMinDays(v); fetch(mode, n, event, v); };

  const filtered = machines.filter(
    (m) =>
      search === "" ||
      m.machine_number.toString().includes(search) ||
      m.model_name.includes(search)
  );

  const modeLabel = mode === "n" ? `${n}の日` : event;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-4">
        <h1 className="text-2xl font-bold text-gray-900">台番分析</h1>

        <EventOrNSelector
          mode={mode} n={n} event={event}
          onModeChange={handleMode} onNChange={handleN} onEventChange={handleEvent}
        />

        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">最低日数:</span>
          <select
            value={minDays}
            onChange={(e) => handleMinDays(Number(e.target.value))}
            className="border border-gray-300 rounded px-2 py-1 text-sm"
          >
            {[3, 5, 8, 10].map((v) => (
              <option key={v} value={v}>{v}日以上</option>
            ))}
          </select>
        </div>

        <input
          type="text"
          placeholder="台番 or 機種名で絞り込み"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="border border-gray-300 rounded px-3 py-1 text-sm w-52"
        />

        <span className="text-sm text-gray-400">{filtered.length}台</span>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-4 py-2 border-b border-gray-100 text-xs text-gray-400">
          {modeLabel} の台番別勝率
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-[#1A3A5C] text-white text-xs">
                <th className="px-3 py-3 text-left w-8">#</th>
                <th className="px-3 py-3 text-left">台番</th>
                <th className="px-3 py-3 text-left">機種名</th>
                <th className="px-3 py-3 text-center">勝率</th>
                <th className="px-3 py-3 text-right">平均差枚</th>
                <th className="px-3 py-3 text-right">累計差枚</th>
                <th className="px-3 py-3 text-center">実績</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {loading ? (
                <tr><td colSpan={7} className="text-center py-12 text-gray-400">読み込み中...</td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan={7} className="text-center py-12 text-gray-400">データなし</td></tr>
              ) : (
                filtered.map((m, i) => (
                  <tr
                    key={m.machine_number}
                    className={`hover:bg-blue-50/30 transition-colors ${
                      m.win_rate >= 0.8 ? "bg-green-50/60" :
                      m.win_rate >= 0.7 ? "bg-green-50/30" : ""
                    }`}
                  >
                    <td className="px-3 py-2.5 text-gray-400 text-xs">{i + 1}</td>
                    <td className="px-3 py-2.5 font-bold text-[#1A3A5C] text-base">{m.machine_number}番</td>
                    <td className="px-3 py-2.5 text-gray-700 max-w-[220px] truncate">{m.model_name}</td>
                    <td className="px-3 py-2.5 text-center"><WinBadge rate={m.win_rate} /></td>
                    <td className="px-3 py-2.5 text-right font-medium">
                      <span className={m.avg_diff >= 0 ? "text-green-700" : "text-red-500"}>
                        {m.avg_diff >= 0 ? "+" : ""}{m.avg_diff.toLocaleString()}枚
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-right text-gray-500 text-xs">
                      {m.total_diff >= 0 ? "+" : ""}{m.total_diff.toLocaleString()}枚
                    </td>
                    <td className="px-3 py-2.5 text-center text-gray-400 text-xs">{m.n_days}日</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
