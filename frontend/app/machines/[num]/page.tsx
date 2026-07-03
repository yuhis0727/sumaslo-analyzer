"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import axios from "axios";
import Link from "next/link";
import { ResponsiveLine } from "@nivo/line";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

type Monthly = { month: string; avg_diff: number; win_rate: number; n: number };
type EventStat = { n_days: number; win_rate: number; avg_diff: number };
type DayRecord = { date: string; model_name: string; total_diff: number | null; game_count: number | null; day_of_week: string; day: number };

type Detail = {
  machine_number: number;
  machine_type: string;
  model_name: string;
  summary: { n_days: number; win_rate: number; avg_diff: number; total_diff: number };
  monthly: Monthly[];
  event_stats: Record<string, EventStat>;
  n_day_stats: Record<string, EventStat>;
  plain_stats: EventStat | null;
  records: DayRecord[];
};

function diffColor(v: number) { return v >= 0 ? "text-green-600" : "text-red-500"; }
function diffStr(v: number) { return `${v >= 0 ? "+" : ""}${v.toLocaleString()}`; }
function winBadge(r: number) {
  const pct = Math.round(r * 100);
  const cls = pct >= 80 ? "bg-green-600 text-white" : pct >= 65 ? "bg-green-400 text-white" : pct >= 50 ? "bg-yellow-100 text-yellow-800" : "bg-gray-100 text-gray-500";
  return <span className={`inline-block px-2 py-0.5 rounded text-xs font-bold ${cls}`}>{pct}%</span>;
}

export default function MachineDetailPage() {
  const { num } = useParams<{ num: string }>();
  const [data, setData] = useState<Detail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get<Detail>(`${API}/api/data/machine/${num}`)
      .then(r => setData(r.data))
      .finally(() => setLoading(false));
  }, [num]);

  if (loading) return <div className="py-16 text-center text-gray-400">読み込み中...</div>;
  if (!data) return <div className="py-16 text-center text-red-500">データが見つかりません</div>;

  const maxAbsDiff = Math.max(...data.monthly.map(m => Math.abs(m.avg_diff)), 1);

  const trendData = [{
    id: "diff",
    data: data.records
      .filter(r => r.total_diff != null)
      .map(r => ({ x: r.date, y: r.total_diff as number })),
  }];
  const typeBadgeClass = data.machine_type === "A"
    ? "bg-green-100 text-green-700"
    : data.machine_type === "BT"
    ? "bg-purple-100 text-purple-700"
    : "bg-blue-100 text-blue-700";
  const typeLabel = data.machine_type === "A" ? "Aタイプ" : data.machine_type + "機";

  return (
    <div className="space-y-6">
      {/* ヘッダー */}
      <div className="flex items-start gap-4">
        <Link href="/machines" className="text-gray-400 hover:text-gray-600 mt-1">← 台番一覧</Link>
        <div>
          <div className="flex items-center gap-3">
            <div className="text-3xl font-bold text-[#1A3A5C]">{data.machine_number}番</div>
            <span className={`text-xs font-bold px-2 py-0.5 rounded ${typeBadgeClass}`}>{typeLabel}</span>
          </div>
          <Link href={`/models/${encodeURIComponent(data.model_name)}`} className="text-gray-600 hover:underline text-lg">
            {data.model_name}
          </Link>
        </div>
      </div>

      {/* サマリーカード */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: "全期間勝率", value: winBadge(data.summary.win_rate) },
          { label: "平均差枚", value: <span className={`text-xl font-bold ${diffColor(data.summary.avg_diff)}`}>{diffStr(data.summary.avg_diff)}</span> },
          { label: "累計差枚", value: <span className={`text-xl font-bold ${diffColor(data.summary.total_diff)}`}>{diffStr(data.summary.total_diff)}</span> },
          { label: "データ日数", value: <span className="text-xl font-bold text-gray-800">{data.summary.n_days}日</span> },
        ].map(c => (
          <div key={c.label} className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-xs text-gray-500 mb-1">{c.label}</div>
            {c.value}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* 月別差枚バーチャート */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="font-semibold text-gray-700 mb-4">月別平均差枚</h2>
          <div className="space-y-2">
            {data.monthly.map(m => {
              const pct = (Math.abs(m.avg_diff) / maxAbsDiff) * 100;
              return (
                <div key={m.month} className="flex items-center gap-2 text-sm">
                  <span className="w-16 text-gray-500 shrink-0">{m.month.slice(5)}月</span>
                  <div className="flex-1 flex items-center gap-1">
                    <div className="flex-1 bg-gray-100 rounded-full h-5 relative overflow-hidden">
                      <div
                        className={`h-full rounded-full ${m.avg_diff >= 0 ? "bg-green-400" : "bg-red-400"}`}
                        style={{ width: `${pct}%` }}
                      />
                      <span className={`absolute inset-0 flex items-center pl-2 text-xs font-medium ${m.avg_diff >= 0 ? "text-green-900" : "text-red-900"}`}>
                        {diffStr(m.avg_diff)}
                      </span>
                    </div>
                  </div>
                  <span className="w-8 text-right text-xs text-gray-400">{Math.round(m.win_rate * 100)}%</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* イベント別・N日別集計 */}
        <div className="space-y-4">
          {(Object.keys(data.event_stats).length > 0 || data.plain_stats) && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h2 className="font-semibold text-gray-700 mb-3">イベント別</h2>
              <table className="w-full text-sm">
                <thead className="text-xs text-gray-500">
                  <tr><th className="text-left pb-2">日種別</th><th className="text-right pb-2">回数</th><th className="text-right pb-2">勝率</th><th className="text-right pb-2">平均差枚</th></tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {Object.entries(data.event_stats).map(([name, s]) => (
                    <tr key={name}>
                      <td className="py-1.5 text-gray-700">{name}</td>
                      <td className="py-1.5 text-right text-gray-400">{s.n_days}回</td>
                      <td className="py-1.5 text-right">{winBadge(s.win_rate)}</td>
                      <td className={`py-1.5 text-right font-mono font-medium ${diffColor(s.avg_diff)}`}>{diffStr(s.avg_diff)}</td>
                    </tr>
                  ))}
                  {data.plain_stats && (
                    <tr className="bg-gray-50/60">
                      <td className="py-1.5 text-gray-500 text-xs">平常日（Nの日・イベント以外）</td>
                      <td className="py-1.5 text-right text-gray-400">{data.plain_stats.n_days}回</td>
                      <td className="py-1.5 text-right">{winBadge(data.plain_stats.win_rate)}</td>
                      <td className={`py-1.5 text-right font-mono font-medium ${diffColor(data.plain_stats.avg_diff)}`}>{diffStr(data.plain_stats.avg_diff)}</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}

          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h2 className="font-semibold text-gray-700 mb-3">Nの日別</h2>
            <table className="w-full text-sm">
              <thead className="text-xs text-gray-500">
                <tr><th className="text-left pb-2">N</th><th className="text-right pb-2">回数</th><th className="text-right pb-2">勝率</th><th className="text-right pb-2">平均差枚</th></tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {Object.entries(data.n_day_stats).sort((a, b) => Number(a[0]) - Number(b[0])).map(([n, s]) => (
                  <tr key={n}>
                    <td className="py-1.5 font-bold text-[#1A3A5C]">{n}の日</td>
                    <td className="py-1.5 text-right text-gray-400">{s.n_days}回</td>
                    <td className="py-1.5 text-right">{winBadge(s.win_rate)}</td>
                    <td className={`py-1.5 text-right font-mono font-medium ${diffColor(s.avg_diff)}`}>{diffStr(s.avg_diff)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* 差枚推移グラフ */}
      {trendData[0].data.length > 1 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="font-semibold text-gray-700 mb-3">差枚推移（全期間）</h2>
          <div className="h-52">
            <ResponsiveLine
              data={trendData}
              margin={{ top: 8, right: 16, bottom: 48, left: 68 }}
              xScale={{ type: "time", format: "%Y-%m-%d", useUTC: false, precision: "day" }}
              xFormat="time:%m/%d"
              yScale={{ type: "linear", stacked: false, min: "auto", max: "auto" }}
              axisBottom={{
                format: "%m/%d",
                tickValues: "every 2 weeks",
                tickRotation: -35,
                tickSize: 4,
              }}
              axisLeft={{ tickSize: 3, tickValues: 5, legend: "差枚", legendOffset: -55, legendPosition: "middle" }}
              colors={["#3b82f6"]}
              lineWidth={1.5}
              pointSize={3}
              pointColor="#3b82f6"
              enableArea
              areaOpacity={0.08}
              enableCrosshair
              markers={[{ axis: "y", value: 0, lineStyle: { stroke: "#9ca3af", strokeWidth: 1, strokeDasharray: "4 4" } }]}
              tooltip={({ point }) => (
                <div className="bg-white border border-gray-200 rounded shadow-sm px-2 py-1 text-xs">
                  <span className="text-gray-500">{point.data.xFormatted}</span>
                  <span className={`ml-2 font-bold ${Number(point.data.y) >= 0 ? "text-green-600" : "text-red-500"}`}>
                    {Number(point.data.y) >= 0 ? "+" : ""}{Number(point.data.y).toLocaleString()}
                  </span>
                </div>
              )}
              theme={{ axis: { ticks: { text: { fontSize: 10, fill: "#9ca3af" } } } }}
            />
          </div>
        </div>
      )}

      {/* 日別履歴 */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="p-4 border-b border-gray-100 font-semibold text-gray-700">日別履歴（{data.records.length}日）</div>
        <div className="overflow-x-auto max-h-96 overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600 text-xs sticky top-0">
              <tr>
                <th className="px-4 py-2 text-left">日付</th>
                <th className="px-4 py-2 text-left">曜</th>
                <th className="px-4 py-2 text-left">機種名</th>
                <th className="px-4 py-2 text-right">差枚</th>
                <th className="px-4 py-2 text-right">G数</th>
              </tr>
            </thead>
            <tbody>
              {[...data.records].reverse().map((r: DayRecord, i) => (
                <tr key={i} className={`border-t border-gray-50 hover:bg-gray-50 ${(r.total_diff ?? 0) >= 0 ? "bg-green-50/20" : ""}`}>
                  <td className="px-4 py-2 font-mono text-gray-600">{r.date}</td>
                  <td className="px-4 py-2 text-gray-400">{r.day_of_week}</td>
                  <td className="px-4 py-2 text-gray-600 truncate max-w-[200px]">{r.model_name}</td>
                  <td className={`px-4 py-2 text-right font-mono font-medium ${diffColor(r.total_diff ?? 0)}`}>
                    {r.total_diff != null ? diffStr(r.total_diff) : "—"}
                  </td>
                  <td className="px-4 py-2 text-right text-gray-400">{r.game_count?.toLocaleString() ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
