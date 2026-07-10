"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import { API } from "./lib/api";
import { diffStr } from "./lib/format";
import { WinBadge, DiffText, DowBadge } from "./components/Badges";
import { LoadingState, ErrorAlert } from "./components/StateViews";
import { ResponsiveTable } from "./components/ResponsiveTable";

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

/** イベント日（7の日・ニャンギラス・月末大田区活性化）判定 */
const isEventDay = (day: number) => [1, 7].includes(day % 10) || day === 30;

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

  if (loading) return <LoadingState label="データ読み込み中..." />;

  if (error) return (
    <div className="space-y-2">
      <ErrorAlert message={`API接続エラー: ${error}`} />
      <p className="text-sm text-gray-500">バックエンドが起動しているか確認してください（{API}）</p>
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
        <DowBadge dow={summary.day_of_week} suffix="曜日" />
        {summary.event_n ? (
          <span className="bg-brand text-white px-4 py-1 rounded-full text-sm font-bold">
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
            <ResponsiveTable
              loading={false}
              empty={summary.top_machines.length === 0}
              mobile={summary.top_machines.slice(0, 10).map((m, i) => (
                <div key={m.machine_number} className="px-4 py-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-baseline gap-2 min-w-0">
                      <span className="text-xs text-gray-400 shrink-0">{i + 1}</span>
                      <span className="font-bold text-brand text-lg shrink-0">{m.machine_number}番</span>
                      <span className="text-sm text-gray-600 truncate">{m.model_name}</span>
                    </div>
                    <WinBadge rate={m.win_rate} />
                  </div>
                  <div className="flex items-center gap-3 mt-1.5 text-xs text-gray-500">
                    <span className="text-sm font-medium"><DiffText value={m.avg_diff} unit="枚" /></span>
                    <span>{m.n_days}日</span>
                  </div>
                </div>
              ))}
              desktop={
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
                        <td className="px-3 py-2.5 font-bold text-brand">
                          {m.machine_number}番
                        </td>
                        <td className="px-3 py-2.5 text-gray-700 max-w-[200px] truncate">
                          {m.model_name}
                        </td>
                        <td className="px-3 py-2.5 text-center">
                          <WinBadge rate={m.win_rate} />
                        </td>
                        <td className="px-3 py-2.5 text-right">
                          <DiffText value={m.avg_diff} unit="枚" />
                        </td>
                        <td className="px-3 py-2.5 text-center text-gray-400 text-xs">
                          {m.n_days}日
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              }
            />
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
                    {diffStr(m.avg_diff)}
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
        <ResponsiveTable
          loading={false}
          empty={recent.length === 0}
          mobile={recent.map((r) => {
            const d = new Date(r.date);
            return (
              <div key={r.date} className={`px-4 py-3 ${isEventDay(d.getDate()) ? "bg-blue-50/40" : ""}`}>
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-900">{`${d.getMonth() + 1}/${d.getDate()}`}</span>
                    <DowBadge dow={r.day_of_week} />
                  </div>
                  <WinBadge rate={r.win_rate} />
                </div>
                <div className="flex items-center gap-3 mt-1.5 text-xs text-gray-500">
                  <span className="text-sm font-medium"><DiffText value={r.avg_diff} unit="枚" /></span>
                  <span>{r.win_machines}/{r.total_machines}台</span>
                </div>
              </div>
            );
          })}
          desktop={
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
                  return (
                    <tr key={r.date} className={`hover:bg-gray-50 ${isEventDay(d.getDate()) ? "bg-blue-50/40" : ""}`}>
                      <td className="px-4 py-2.5 font-medium text-gray-900">
                        {`${d.getMonth() + 1}/${d.getDate()}`}
                      </td>
                      <td className="px-4 py-2.5 text-center">
                        <DowBadge dow={r.day_of_week} />
                      </td>
                      <td className="px-4 py-2.5 text-center text-gray-600">{r.total_machines}</td>
                      <td className="px-4 py-2.5 text-center text-gray-600">{r.win_machines}</td>
                      <td className="px-4 py-2.5 text-center">
                        <WinBadge rate={r.win_rate} />
                      </td>
                      <td className="px-4 py-2.5 text-right">
                        <DiffText value={r.avg_diff} unit="枚" />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          }
        />
      </div>
    </div>
  );
}
