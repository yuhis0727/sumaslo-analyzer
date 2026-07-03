"use client";

import { useEffect, useState } from "react";
import axios from "axios";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";
const DOW_COLOR: Record<string, string> = {
  月: "bg-blue-100 text-blue-800",
  火: "bg-red-100 text-red-800",
  水: "bg-cyan-100 text-cyan-800",
  木: "bg-green-100 text-green-800",
  金: "bg-yellow-100 text-yellow-800",
  土: "bg-purple-100 text-purple-800",
  日: "bg-pink-100 text-pink-800",
};

type MachinePick = {
  machine_number: number;
  model_name: string;
  win_rate: number;
  avg_diff: number;
  n_days: number;
};

type ModelStat = {
  model_name: string;
  win_rate: number;
  avg_diff: number;
  n_days: number;
};

type Summary = {
  today: string;
  day_of_week: string;
  event_n: number | null;
  event_dates: string[];
  n_event_days: number;
  top_machines: MachinePick[];
  top_models: ModelStat[];
  message?: string;
};

type RecentDay = {
  date: string;
  day_of_week: string;
  total_machines: number;
  win_machines: number;
  win_rate: number;
  avg_diff: number;
};

function WinBadge({ rate }: { rate: number }) {
  const pct = Math.round(rate * 100);
  const color =
    pct >= 80 ? "bg-green-600 text-white" :
    pct >= 70 ? "bg-green-400 text-white" :
    pct >= 60 ? "bg-green-200 text-green-900" :
    pct >= 50 ? "bg-yellow-100 text-yellow-800" :
    "bg-gray-100 text-gray-600";
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-sm font-bold ${color}`}>
      {pct}%
    </span>
  );
}

function DiffBadge({ diff }: { diff: number }) {
  const color = diff >= 3000 ? "text-green-700 font-bold" :
                diff >= 1000 ? "text-green-600" :
                diff >= 0    ? "text-gray-700" :
                               "text-red-500";
  return <span className={color}>{diff >= 0 ? "+" : ""}{diff.toLocaleString()}枚</span>;
}

export default function Dashboard() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [recent, setRecent] = useState<RecentDay[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      axios.get<Summary>(`${API}/api/data/summary`),
      axios.get<RecentDay[]>(`${API}/api/data/recent?days=7`),
    ])
      .then(([s, r]) => {
        setSummary(s.data);
        setRecent(r.data);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="flex items-center justify-center h-64 text-gray-400 text-lg">
      データ読み込み中...
    </div>
  );

  if (error) return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-red-700">
      <p className="font-bold">API接続エラー</p>
      <p className="text-sm mt-1">{error}</p>
      <p className="text-sm mt-2 text-gray-500">バックエンドが起動しているか確認してください（{API}）</p>
    </div>
  );

  if (!summary) return null;

  const today = new Date(summary.today);
  const dateStr = `${today.getMonth() + 1}/${today.getDate()}`;

  return (
    <div className="space-y-6">
      {/* ヘッダー情報 */}
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold text-gray-900">ダッシュボード</h1>
        <span className="text-gray-500 text-lg">{dateStr}</span>
        <span className={`px-3 py-1 rounded-full text-sm font-bold ${DOW_COLOR[summary.day_of_week] ?? "bg-gray-100"}`}>
          {summary.day_of_week}曜日
        </span>
        {summary.event_n ? (
          <span className="bg-[#1A3A5C] text-white px-4 py-1 rounded-full text-sm font-bold">
            🎯 {summary.event_n}の日（{summary.n_event_days}日分データ）
          </span>
        ) : (
          <span className="bg-gray-200 text-gray-600 px-4 py-1 rounded-full text-sm">
            通常日
          </span>
        )}
      </div>

      {summary.message && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-yellow-800">
          {summary.message}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* おすすめ台 TOP10 */}
        {summary.event_n && (
          <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-200">
            <div className="px-5 py-4 border-b border-gray-100">
              <h2 className="font-bold text-gray-900">
                🏆 {summary.event_n}の日 おすすめ台 TOP10
              </h2>
              <p className="text-xs text-gray-400 mt-0.5">現稼働台限定・最低8日実績</p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 text-gray-500 text-xs">
                    <th className="px-3 py-2 text-left w-8">#</th>
                    <th className="px-3 py-2 text-left">台番</th>
                    <th className="px-3 py-2 text-left">機種</th>
                    <th className="px-3 py-2 text-center">勝率</th>
                    <th className="px-3 py-2 text-right">平均差枚</th>
                    <th className="px-3 py-2 text-center">実績日数</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {summary.top_machines.slice(0, 10).map((m, i) => (
                    <tr key={m.machine_number} className="hover:bg-gray-50 transition-colors">
                      <td className="px-3 py-2.5 text-gray-400 text-xs">{i + 1}</td>
                      <td className="px-3 py-2.5 font-bold text-[#1A3A5C]">
                        {m.machine_number}番
                      </td>
                      <td className="px-3 py-2.5 text-gray-700 max-w-[200px] truncate">
                        {m.model_name}
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        <WinBadge rate={m.win_rate} />
                      </td>
                      <td className="px-3 py-2.5 text-right">
                        <DiffBadge diff={m.avg_diff} />
                      </td>
                      <td className="px-3 py-2.5 text-center text-gray-400 text-xs">
                        {m.n_days}日
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* 機種別勝率 */}
        {summary.event_n && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200">
            <div className="px-5 py-4 border-b border-gray-100">
              <h2 className="font-bold text-gray-900">
                📊 {summary.event_n}の日 機種別
              </h2>
            </div>
            <div className="p-4 space-y-2">
              {summary.top_models.slice(0, 12).map((m) => (
                <div key={m.model_name} className="flex items-center gap-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-gray-700 truncate">{m.model_name}</p>
                  </div>
                  <WinBadge rate={m.win_rate} />
                  <span className="text-xs text-gray-400 w-16 text-right">
                    {m.avg_diff >= 0 ? "+" : ""}{m.avg_diff.toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 直近7日サマリー */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200">
        <div className="px-5 py-4 border-b border-gray-100">
          <h2 className="font-bold text-gray-900">📅 直近7日の全台成績</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-gray-500 text-xs">
                <th className="px-4 py-2 text-left">日付</th>
                <th className="px-4 py-2 text-center">曜日</th>
                <th className="px-4 py-2 text-center">稼働台数</th>
                <th className="px-4 py-2 text-center">勝ち台数</th>
                <th className="px-4 py-2 text-center">全台勝率</th>
                <th className="px-4 py-2 text-right">平均差枚</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {recent.map((r) => {
                const d = new Date(r.date);
                const isEvent = [3, 7, 13, 17, 23, 27].includes(d.getDate()) ||
                                (d.getDate() % 10 > 0 && d.getDate() % 10 <= 9);
                return (
                  <tr key={r.date} className={`hover:bg-gray-50 ${isEvent ? "bg-blue-50/40" : ""}`}>
                    <td className="px-4 py-2.5 font-medium text-gray-900">
                      {`${d.getMonth()+1}/${d.getDate()}`}
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${DOW_COLOR[r.day_of_week] ?? "bg-gray-100"}`}>
                        {r.day_of_week}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-center text-gray-600">{r.total_machines}</td>
                    <td className="px-4 py-2.5 text-center text-gray-600">{r.win_machines}</td>
                    <td className="px-4 py-2.5 text-center">
                      <WinBadge rate={r.win_rate} />
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <DiffBadge diff={r.avg_diff} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
