"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import Link from "next/link";
import EventOrNSelector, { FilterMode, EventName } from "../components/EventOrNSelector";
import TypeFilterTabs, { TypeFilter } from "../components/TypeFilterTabs";
import { MachineType, WinBadge } from "../components/Badges";
import { ResponsiveTable } from "../components/ResponsiveTable";
import { API } from "../lib/api";
import { diffStr, diffColor } from "../lib/format";

interface Machine {
  machine_number: number;
  model_name: string;
  machine_type: MachineType;
  win_rate: number;
  avg_diff: number;
  total_diff: number;
  n_days: number;
}

export default function MachinesPage() {
  const [mode, setMode] = useState<FilterMode>("n");
  const [n, setN] = useState(7);
  const [event, setEvent] = useState<EventName>("ニャンギラス");
  const [minDays, setMinDays] = useState(8);
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("all");
  const [machines, setMachines] = useState<Machine[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");

  const buildParams = (m: FilterMode, nVal: number, ev: EventName, min: number) => {
    // 台番/機種名の検索は取得後にクライアント側で絞り込むため、
    // 店舗の総台数(715台)を上回る上限を指定して取りこぼしを防ぐ
    const p = new URLSearchParams({ min_days: String(min), limit: "800" });
    if (m === "n") p.set("n", String(nVal));
    else if (m === "event") p.set("event", ev);
    else if (m === "plain") p.set("plain", "true");
    else p.set("all_days", "true");
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
      (typeFilter === "all" || m.machine_type === typeFilter) &&
      (search === "" ||
        m.machine_number.toString().includes(search) ||
        m.model_name.includes(search))
  );

  const modeLabel =
    mode === "n" ? `${n}の日` :
    mode === "event" ? event :
    mode === "plain" ? "平常日" : "全期間";

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <h1 className="text-2xl font-bold text-gray-900">台番分析</h1>
        <span className="text-sm text-gray-400 shrink-0">{filtered.length}台</span>
      </div>

      <div className="flex flex-col md:flex-row md:items-center gap-2 md:gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <EventOrNSelector
            mode={mode} n={n} event={event}
            onModeChange={handleMode} onNChange={handleN} onEventChange={handleEvent}
          />
          <TypeFilterTabs value={typeFilter} onChange={setTypeFilter} />
        </div>

        <div className="flex items-center gap-2 md:ml-auto">
          <select
            value={minDays}
            onChange={(e) => handleMinDays(Number(e.target.value))}
            className="border border-gray-300 rounded px-2 py-1.5 text-sm shrink-0"
          >
            {[3, 5, 8, 10].map((v) => (
              <option key={v} value={v}>{v}日以上</option>
            ))}
          </select>

          <input
            type="text"
            placeholder="台番 or 機種名で絞り込み"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm flex-1 md:w-52"
          />
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-4 py-2 border-b border-gray-100 text-xs text-gray-400">
          {modeLabel} の台番別勝率
        </div>

        <ResponsiveTable
          loading={loading}
          empty={filtered.length === 0}
          mobile={filtered.map((m, i) => (
            <div
              key={m.machine_number}
              className={`px-4 py-3 ${
                m.win_rate >= 0.8 ? "bg-green-50/60" :
                m.win_rate >= 0.7 ? "bg-green-50/30" : ""
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-baseline gap-2 min-w-0">
                  <span className="text-xs text-gray-400 shrink-0">{i + 1}</span>
                  <Link href={`/machines/${m.machine_number}`} className="font-bold text-brand text-lg shrink-0 hover:underline">
                    {m.machine_number}番
                  </Link>
                  <Link
                    href={`/models/${encodeURIComponent(m.model_name)}`}
                    className="text-sm text-gray-600 truncate hover:text-brand hover:underline"
                  >
                    {m.model_name}
                  </Link>
                </div>
                <WinBadge rate={m.win_rate} />
              </div>
              <div className="flex items-center gap-3 mt-1.5 text-xs text-gray-500">
                <span className={`text-sm font-medium ${diffColor(m.avg_diff)}`}>{diffStr(m.avg_diff)}枚</span>
                <span>累計{diffStr(m.total_diff)}枚</span>
                <span>{m.n_days}日</span>
              </div>
            </div>
          ))}
          desktop={
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-brand text-white text-xs">
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
                {filtered.map((m, i) => (
                  <tr
                    key={m.machine_number}
                    className={`hover:bg-blue-50/30 transition-colors ${
                      m.win_rate >= 0.8 ? "bg-green-50/60" :
                      m.win_rate >= 0.7 ? "bg-green-50/30" : ""
                    }`}
                  >
                    <td className="px-3 py-2.5 text-gray-400 text-xs">{i + 1}</td>
                    <td className="px-3 py-2.5 font-bold text-brand text-base">
                      <Link href={`/machines/${m.machine_number}`} className="hover:underline">{m.machine_number}番</Link>
                    </td>
                    <td className="px-3 py-2.5 text-gray-700 max-w-[220px] truncate">
                      <Link href={`/models/${encodeURIComponent(m.model_name)}`} className="hover:underline hover:text-brand">{m.model_name}</Link>
                    </td>
                    <td className="px-3 py-2.5 text-center"><WinBadge rate={m.win_rate} /></td>
                    <td className="px-3 py-2.5 text-right font-medium">
                      <span className={diffColor(m.avg_diff)}>{diffStr(m.avg_diff)}枚</span>
                    </td>
                    <td className="px-3 py-2.5 text-right text-gray-500 text-xs">
                      {diffStr(m.total_diff)}枚
                    </td>
                    <td className="px-3 py-2.5 text-center text-gray-400 text-xs">{m.n_days}日</td>
                  </tr>
                ))}
              </tbody>
            </table>
          }
        />
      </div>
    </div>
  );
}
