"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import Link from "next/link";
import EventOrNSelector, { FilterMode, EventName } from "../components/EventOrNSelector";
import TypeFilterTabs, { TypeFilter } from "../components/TypeFilterTabs";
import { MachineType, WinBar, TypeBadge } from "../components/Badges";
import { API } from "../lib/api";
import { diffStr } from "../lib/format";

type ModelStat = {
  model_name: string;
  machine_type: MachineType;
  n_machines: number;
  win_rate: number;
  avg_diff: number;
  n_days: number;
  monthly_avg: Record<string, number>;
};

export default function ModelsPage() {
  const [mode, setMode] = useState<FilterMode>("n");
  const [n, setN] = useState(7);
  const [event, setEvent] = useState<EventName>("ニャンギラス");
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("all");
  const [models, setModels] = useState<ModelStat[]>([]);
  const [loading, setLoading] = useState(false);

  const fetch = (m: FilterMode, nVal: number, ev: EventName) => {
    setLoading(true);
    const p = m === "n" ? `n=${nVal}` : m === "event" ? `event=${encodeURIComponent(ev)}` : `plain=true`;
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
  const filtered = typeFilter === "all" ? models : models.filter(m => m.machine_type === typeFilter);
  const recentMonths = models.length > 0 ? Object.keys(models[0].monthly_avg ?? {}).sort().slice(-3) : [];

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-4">
        <h1 className="text-2xl font-bold text-gray-900">機種別分析</h1>
        <EventOrNSelector
          mode={mode} n={n} event={event}
          onModeChange={handleMode} onNChange={handleN} onEventChange={handleEvent}
        />
      </div>

      <TypeFilterTabs value={typeFilter} onChange={setTypeFilter} allLabel="全機種" />

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-5 py-3 border-b border-gray-100 text-sm text-gray-400">
          {modeLabel} の機種別勝率（機種全体の平均）
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-brand text-white text-xs">
                <th className="px-4 py-3 text-left w-8">#</th>
                <th className="px-4 py-3 text-left">機種名</th>
                <th className="px-4 py-3 text-center">台数</th>
                <th className="px-4 py-3 text-left">勝率</th>
                <th className="px-4 py-3 text-right">平均差枚</th>
                {recentMonths.map(ym => (
                  <th key={ym} className="px-3 py-3 text-right whitespace-nowrap">{ym.slice(5)}月平均</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {loading ? (
                <tr><td colSpan={5 + recentMonths.length} className="text-center py-12 text-gray-400">読み込み中...</td></tr>
              ) : (
                filtered.map((m, i) => (
                  <tr key={m.model_name} className={`hover:bg-gray-50 ${m.win_rate >= 0.65 ? "bg-green-50/40" : ""}`}>
                    <td className="px-4 py-2.5 text-gray-400 text-xs">{i + 1}</td>
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-2">
                        <TypeBadge type={m.machine_type} short />
                        <Link href={`/models/${encodeURIComponent(m.model_name)}`} className="font-medium text-gray-800 hover:text-brand hover:underline">
                          {m.model_name}
                        </Link>
                      </div>
                    </td>
                    <td className="px-4 py-2.5 text-center text-gray-500">{m.n_machines}台</td>
                    <td className="px-4 py-2.5"><WinBar rate={m.win_rate} /></td>
                    <td className="px-4 py-2.5 text-right">
                      <span className={m.avg_diff >= 0 ? "text-green-700 font-medium" : "text-red-500"}>
                        {diffStr(m.avg_diff)}枚
                      </span>
                    </td>
                    {recentMonths.map(ym => {
                      const v = m.monthly_avg?.[ym];
                      return (
                        <td key={ym} className={`px-3 py-2.5 text-right text-xs font-mono ${v == null ? "text-gray-300" : v >= 0 ? "text-green-600" : "text-red-400"}`}>
                          {v == null ? "—" : diffStr(v)}
                        </td>
                      );
                    })}
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
