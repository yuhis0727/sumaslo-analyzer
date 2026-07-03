"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import EventOrNSelector, { FilterMode, EventName } from "../components/EventOrNSelector";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

type ModelStat = {
  model_name: string;
  n_machines: number;
  win_rate: number;
  avg_diff: number;
  n_days: number;
};

function WinBar({ rate }: { rate: number }) {
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

export default function ModelsPage() {
  const [mode, setMode] = useState<FilterMode>("n");
  const [n, setN] = useState(7);
  const [event, setEvent] = useState<EventName>("ニャンギラス");
  const [models, setModels] = useState<ModelStat[]>([]);
  const [loading, setLoading] = useState(false);

  const fetch = (m: FilterMode, nVal: number, ev: EventName) => {
    setLoading(true);
    const p = m === "n" ? `n=${nVal}` : `event=${encodeURIComponent(ev)}`;
    axios
      .get<ModelStat[]>(`${API}/api/data/models?${p}`)
      .then((r) => setModels(r.data))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetch(mode, n, event); }, []);

  const handleMode = (m: FilterMode) => { setMode(m); fetch(m, n, event); };
  const handleN = (v: number) => { setN(v); fetch(mode, v, event); };
  const handleEvent = (e: EventName) => { setEvent(e); fetch(mode, n, e); };

  const modeLabel = mode === "n" ? `${n}の日` : event;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-4">
        <h1 className="text-2xl font-bold text-gray-900">機種別分析</h1>
        <EventOrNSelector
          mode={mode} n={n} event={event}
          onModeChange={handleMode} onNChange={handleN} onEventChange={handleEvent}
        />
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-5 py-3 border-b border-gray-100 text-sm text-gray-400">
          {modeLabel} の機種別勝率（機種全体の平均）
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-[#1A3A5C] text-white text-xs">
                <th className="px-4 py-3 text-left w-8">#</th>
                <th className="px-4 py-3 text-left">機種名</th>
                <th className="px-4 py-3 text-center">台数</th>
                <th className="px-4 py-3 text-left">勝率</th>
                <th className="px-4 py-3 text-right">平均差枚</th>
                <th className="px-4 py-3 text-center">延べ日数</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {loading ? (
                <tr><td colSpan={6} className="text-center py-12 text-gray-400">読み込み中...</td></tr>
              ) : (
                models.map((m, i) => (
                  <tr key={m.model_name} className={`hover:bg-gray-50 ${m.win_rate >= 0.65 ? "bg-green-50/40" : ""}`}>
                    <td className="px-4 py-2.5 text-gray-400 text-xs">{i + 1}</td>
                    <td className="px-4 py-2.5 font-medium text-gray-800">{m.model_name}</td>
                    <td className="px-4 py-2.5 text-center text-gray-500">{m.n_machines}台</td>
                    <td className="px-4 py-2.5"><WinBar rate={m.win_rate} /></td>
                    <td className="px-4 py-2.5 text-right">
                      <span className={m.avg_diff >= 0 ? "text-green-700 font-medium" : "text-red-500"}>
                        {m.avg_diff >= 0 ? "+" : ""}{m.avg_diff.toLocaleString()}枚
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-center text-gray-400 text-xs">{m.n_days}日</td>
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
