"use client";

import { useEffect, useState } from "react";
import axios from "axios";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

type EventMeta = {
  event_name: string;
  note: string;
  total_dates: number;
  dates_in_data: number;
  dates: string[];
};

type DateSummary = {
  date: string;
  day_of_week: string;
  total_machines: number;
  plus_machines: number;
  positive_rate: number;
  avg_diff: number;
};

type ModelRank = {
  model_name: string;
  n_days: number;
  win_rate: number;
  avg_diff: number;
};

type MachineRank = {
  machine_number: number;
  model_name: string;
  n_days: number;
  win_rate: number;
  avg_diff: number;
};

type EventAnalysis = {
  event_name: string;
  note: string;
  dates_summary: DateSummary[];
  top_models: ModelRank[];
  top_machines: MachineRank[];
  overall_avg_diff: number;
};

type Tab = "dates" | "models" | "machines";

export default function EventsPage() {
  const [events, setEvents] = useState<EventMeta[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<EventAnalysis | null>(null);
  const [tab, setTab] = useState<Tab>("dates");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    axios.get<EventMeta[]>(`${API}/api/data/events`).then((res) => {
      setEvents(res.data);
      if (res.data.length > 0) loadAnalysis(res.data[0].event_name);
    });
  }, []);

  const loadAnalysis = async (name: string) => {
    setSelected(name);
    setLoading(true);
    setError("");
    try {
      const res = await axios.get<EventAnalysis>(
        `${API}/api/data/event-analysis?event=${encodeURIComponent(name)}`
      );
      setAnalysis(res.data);
    } catch {
      setError("APIエラー: バックエンドを確認してください");
    } finally {
      setLoading(false);
    }
  };

  const winColor = (r: number) =>
    r >= 0.8 ? "bg-green-100 text-green-700" :
    r >= 0.6 ? "bg-yellow-100 text-yellow-700" :
    "bg-gray-100 text-gray-500";

  const diffColor = (v: number) => v >= 0 ? "text-green-600" : "text-red-500";
  const diffStr = (v: number) => `${v >= 0 ? "+" : ""}${v.toLocaleString()}`;

  const avgAll = analysis?.overall_avg_diff ?? 0;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">イベント別分析</h1>
        <p className="text-sm text-gray-500 mt-1">
          ニャンギラス・大田区活性化・ファン感謝デーの実績を集計します
        </p>
      </div>

      {/* イベント選択 */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {events.map((ev) => (
          <button
            key={ev.event_name}
            onClick={() => loadAnalysis(ev.event_name)}
            className={`text-left p-4 rounded-xl border-2 transition-all ${
              selected === ev.event_name
                ? "border-[#1A3A5C] bg-[#1A3A5C]/5"
                : "border-gray-200 bg-white hover:border-gray-300"
            }`}
          >
            <div className="font-bold text-gray-900 mb-1">{ev.event_name}</div>
            <div className="text-xs text-gray-500 leading-relaxed">{ev.note}</div>
            <div className="mt-2 text-xs text-gray-400">
              データあり: <span className="font-semibold text-gray-700">{ev.dates_in_data}</span>/{ev.total_dates}日
            </div>
          </button>
        ))}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-3 text-sm">{error}</div>
      )}

      {analysis && !loading && (
        <>
          {/* サマリーカード */}
          {(() => {
            const total = analysis.dates_summary.reduce((a, d) => a + d.total_machines, 0);
            const plus  = analysis.dates_summary.reduce((a, d) => a + d.plus_machines, 0);
            const rate  = total > 0 ? plus / total : 0;
            const avgDiff = total > 0
              ? Math.round(analysis.dates_summary.reduce((a, d) => a + d.avg_diff * d.total_machines, 0) / total)
              : 0;
            return (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[
                  { label: "対象日数", value: `${analysis.dates_summary.length}日` },
                  { label: "全体プラス率", value: `${(rate * 100).toFixed(1)}%`, color: rate >= 0.6 ? "text-green-600" : "text-gray-700" },
                  { label: "イベント平均差枚", value: diffStr(avgDiff), color: diffColor(avgDiff) },
                  { label: "全日程平均差枚（比較）", value: diffStr(avgAll), color: diffColor(avgAll) },
                ].map((card) => (
                  <div key={card.label} className="bg-white rounded-xl border border-gray-200 p-4">
                    <div className="text-xs text-gray-500 mb-1">{card.label}</div>
                    <div className={`text-xl font-bold ${card.color ?? "text-gray-900"}`}>{card.value}</div>
                  </div>
                ))}
              </div>
            );
          })()}

          {/* タブ */}
          <div className="flex gap-0 border-b border-gray-200">
            {(["dates", "models", "machines"] as Tab[]).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-5 py-2 text-sm font-medium border-b-2 transition-colors ${
                  tab === t
                    ? "border-[#1A3A5C] text-[#1A3A5C]"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                {t === "dates" ? "日別実績" : t === "models" ? "機種別" : "台番別"}
              </button>
            ))}
          </div>

          {/* 日別実績 */}
          {tab === "dates" && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-gray-600 text-xs uppercase tracking-wide">
                  <tr>
                    <th className="px-4 py-3 text-left">日付</th>
                    <th className="px-4 py-3 text-left">曜日</th>
                    <th className="px-4 py-3 text-right">台数</th>
                    <th className="px-4 py-3 text-right">プラス率</th>
                    <th className="px-4 py-3 text-right">平均差枚</th>
                  </tr>
                </thead>
                <tbody>
                  {analysis.dates_summary.map((d) => (
                    <tr key={d.date} className="border-t border-gray-100 hover:bg-gray-50">
                      <td className="px-4 py-3 font-mono text-gray-700">{d.date}</td>
                      <td className="px-4 py-3 text-gray-500">{d.day_of_week}曜</td>
                      <td className="px-4 py-3 text-right text-gray-500">
                        {d.plus_machines}/{d.total_machines}台
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-bold ${winColor(d.positive_rate)}`}>
                          {(d.positive_rate * 100).toFixed(0)}%
                        </span>
                      </td>
                      <td className={`px-4 py-3 text-right font-mono font-medium ${diffColor(d.avg_diff)}`}>
                        {diffStr(d.avg_diff)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* 機種別 */}
          {tab === "models" && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-gray-600 text-xs uppercase tracking-wide">
                  <tr>
                    <th className="px-4 py-3 text-left">機種名</th>
                    <th className="px-4 py-3 text-right">回数</th>
                    <th className="px-4 py-3 text-right">勝率</th>
                    <th className="px-4 py-3 text-right">平均差枚</th>
                  </tr>
                </thead>
                <tbody>
                  {analysis.top_models.map((m, i) => (
                    <tr key={m.model_name} className="border-t border-gray-100 hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          {i < 3 && (
                            <span className={`text-xs font-bold w-5 h-5 rounded-full flex items-center justify-center shrink-0 ${
                              i === 0 ? "bg-yellow-400 text-white" :
                              i === 1 ? "bg-gray-300 text-gray-700" :
                              "bg-amber-600 text-white"
                            }`}>{i + 1}</span>
                          )}
                          <span className="truncate max-w-[240px]">{m.model_name}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right text-gray-500">{m.n_days}回</td>
                      <td className="px-4 py-3 text-right">
                        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-bold ${winColor(m.win_rate)}`}>
                          {(m.win_rate * 100).toFixed(0)}%
                        </span>
                      </td>
                      <td className={`px-4 py-3 text-right font-mono font-medium ${diffColor(m.avg_diff)}`}>
                        {diffStr(m.avg_diff)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* 台番別 */}
          {tab === "machines" && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-gray-600 text-xs uppercase tracking-wide">
                  <tr>
                    <th className="px-4 py-3 text-left">台番</th>
                    <th className="px-4 py-3 text-left">機種名</th>
                    <th className="px-4 py-3 text-right">回数</th>
                    <th className="px-4 py-3 text-right">勝率</th>
                    <th className="px-4 py-3 text-right">平均差枚</th>
                  </tr>
                </thead>
                <tbody>
                  {analysis.top_machines.map((m, i) => (
                    <tr key={m.machine_number} className="border-t border-gray-100 hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          {i < 3 && (
                            <span className={`text-xs font-bold w-5 h-5 rounded-full flex items-center justify-center shrink-0 ${
                              i === 0 ? "bg-yellow-400 text-white" :
                              i === 1 ? "bg-gray-300 text-gray-700" :
                              "bg-amber-600 text-white"
                            }`}>{i + 1}</span>
                          )}
                          <span className="font-mono font-bold text-[#1A3A5C]">{m.machine_number}番</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-gray-700 truncate max-w-[200px]">{m.model_name}</td>
                      <td className="px-4 py-3 text-right text-gray-500">{m.n_days}回</td>
                      <td className="px-4 py-3 text-right">
                        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-bold ${winColor(m.win_rate)}`}>
                          {(m.win_rate * 100).toFixed(0)}%
                        </span>
                      </td>
                      <td className={`px-4 py-3 text-right font-mono font-medium ${diffColor(m.avg_diff)}`}>
                        {diffStr(m.avg_diff)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {loading && (
        <div className="text-center text-gray-400 py-12">読み込み中...</div>
      )}
    </div>
  );
}
