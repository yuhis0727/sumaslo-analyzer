"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import { ResponsiveTable } from "../../components/ResponsiveTable";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

type WeeklyRow = {
  week: number;
  win_rate: number;
  avg_diff: number;
  vs_store: number;
  n: number;
};

type NewMachineModel = {
  model_name: string;
  machine_type: "AT" | "A" | "BT";
  intro_date: string;
  total_days: number;
  n_data_days: number;
  overall_win_rate: number;
  overall_avg_diff: number;
  weekly: WeeklyRow[];
};

type WeeklyAgg = {
  week: number;
  avg_diff: number;
  win_rate: number;
  n: number;
};

type Response = {
  models: NewMachineModel[];
  weekly_aggregate: WeeklyAgg[];
};

const TYPE_LABEL: Record<string, string> = { AT: "AT", A: "A", BT: "BT" };
const TYPE_COLOR: Record<string, string> = {
  AT: "bg-blue-100 text-blue-700",
  A: "bg-green-100 text-green-700",
  BT: "bg-purple-100 text-purple-700",
};

function DiffCell({ value }: { value: number }) {
  const cls = value >= 0 ? "text-green-700 font-medium" : "text-red-500";
  return <span className={cls}>{value >= 0 ? "+" : ""}{value.toLocaleString()}</span>;
}

function WrCell({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const cls = pct >= 65 ? "text-green-700 font-bold" : pct >= 50 ? "text-yellow-600" : "text-red-500";
  return <span className={cls}>{pct}%</span>;
}

function WeekBadge({ wk, data }: { wk: number; data: WeeklyRow | undefined }) {
  if (!data) return <td className="px-3 py-2 text-center text-gray-300 text-xs">—</td>;
  const bg =
    data.avg_diff >= 200 ? "bg-green-100" :
    data.avg_diff >= 0 ? "bg-yellow-50" :
    "bg-red-50";
  return (
    <td className={`px-3 py-2 text-center text-xs ${bg}`}>
      <div className="font-mono font-medium"><DiffCell value={data.avg_diff} /></div>
      <div className="text-gray-400">{Math.round(data.win_rate * 100)}%</div>
    </td>
  );
}

const WEEKS = [1, 2, 3, 4, 5, 6, 7, 8];

export default function NewMachinesPage() {
  const [data, setData] = useState<Response | null>(null);
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState<"all" | "AT" | "A" | "BT">("all");

  useEffect(() => {
    axios.get<Response>(`${API}/api/data/new-machines`).then(r => {
      setData(r.data);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-gray-400 py-12 text-center">読み込み中...</div>;
  if (!data) return <div className="text-red-400 py-12 text-center">データ取得エラー</div>;

  const agg = data.weekly_aggregate;
  const models = typeFilter === "all" ? data.models : data.models.filter(m => m.machine_type === typeFilter);

  // 仮説検証: 全体的に早い週は回収傾向か
  const earlyAvg = agg.filter(w => w.week <= 2).reduce((s, w) => s + w.avg_diff * w.n, 0) /
    Math.max(1, agg.filter(w => w.week <= 2).reduce((s, w) => s + w.n, 0));
  const laterAvg = agg.filter(w => w.week >= 5).reduce((s, w) => s + w.avg_diff * w.n, 0) /
    Math.max(1, agg.filter(w => w.week >= 5).reduce((s, w) => s + w.n, 0));
  const hypothesisConfirmed = earlyAvg < laterAvg;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">新台分析</h1>
        <p className="text-sm text-gray-500 mt-1">導入後の回収期間を週別データで検証する</p>
      </div>

      {/* 仮説検証サマリー */}
      <div className={`rounded-xl p-4 border ${hypothesisConfirmed ? "bg-amber-50 border-amber-200" : "bg-green-50 border-green-200"}`}>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-lg">{hypothesisConfirmed ? "⚠️" : "✅"}</span>
          <span className="font-bold text-gray-800">
            {hypothesisConfirmed
              ? "新台回収仮説：データで確認"
              : "新台回収仮説：データ上は否定"}
          </span>
        </div>
        <div className="flex gap-6 text-sm">
          <div>
            <span className="text-gray-500">導入1〜2週目平均：</span>
            <span className={`font-bold ml-1 ${earlyAvg >= 0 ? "text-green-700" : "text-red-600"}`}>
              {earlyAvg >= 0 ? "+" : ""}{Math.round(earlyAvg).toLocaleString()}枚
            </span>
          </div>
          <div>
            <span className="text-gray-500">5週目以降平均：</span>
            <span className={`font-bold ml-1 ${laterAvg >= 0 ? "text-green-700" : "text-red-600"}`}>
              {laterAvg >= 0 ? "+" : ""}{Math.round(laterAvg).toLocaleString()}枚
            </span>
          </div>
        </div>
      </div>

      {/* 週別集計グラフ（テーブル形式） */}
      {agg.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100 font-medium text-gray-700 text-sm">
            全新台 導入週別集計
          </div>
          <ResponsiveTable
            loading={false}
            empty={agg.length === 0}
            mobile={agg.map(w => {
              const barW = Math.min(100, Math.abs(w.avg_diff) / 20);
              return (
                <div key={w.week} className={`px-4 py-2.5 ${w.week <= 2 ? "bg-amber-50/40" : ""}`}>
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium text-gray-700 text-sm">
                      {w.week === 8 ? "8週目〜" : `${w.week}週目`}
                      {w.week <= 2 && <span className="ml-2 text-xs text-amber-600 font-normal">回収期?</span>}
                    </span>
                    <span className="font-mono text-sm"><DiffCell value={w.avg_diff} /></span>
                  </div>
                  <div className="flex items-center justify-between gap-2 mt-1 text-xs text-gray-400">
                    <WrCell value={w.win_rate} />
                    <span>{w.n}台日</span>
                  </div>
                  <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden mt-1.5">
                    <div
                      className={`h-2 rounded-full ${w.avg_diff >= 0 ? "bg-green-400" : "bg-red-400"}`}
                      style={{ width: `${barW}%` }}
                    />
                  </div>
                </div>
              );
            })}
            desktop={
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 text-xs text-gray-500">
                    <th className="px-4 py-2 text-left">導入週</th>
                    <th className="px-4 py-2 text-right">平均差枚</th>
                    <th className="px-4 py-2 text-right">勝率</th>
                    <th className="px-4 py-2 text-right">サンプル数</th>
                    <th className="px-4 py-2 text-left">回収度</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {agg.map(w => {
                    const barW = Math.min(100, Math.abs(w.avg_diff) / 20);
                    return (
                      <tr key={w.week} className={w.week <= 2 ? "bg-amber-50/40" : ""}>
                        <td className="px-4 py-2.5 font-medium text-gray-700">
                          {w.week === 8 ? "8週目〜" : `${w.week}週目`}
                          {w.week <= 2 && <span className="ml-2 text-xs text-amber-600 font-normal">回収期?</span>}
                        </td>
                        <td className="px-4 py-2.5 text-right font-mono">
                          <DiffCell value={w.avg_diff} />
                        </td>
                        <td className="px-4 py-2.5 text-right">
                          <WrCell value={w.win_rate} />
                        </td>
                        <td className="px-4 py-2.5 text-right text-gray-400 text-xs">{w.n}台日</td>
                        <td className="px-4 py-2.5">
                          <div className="flex items-center gap-1">
                            <div className="w-24 h-2 bg-gray-100 rounded-full overflow-hidden">
                              <div
                                className={`h-2 rounded-full ${w.avg_diff >= 0 ? "bg-green-400" : "bg-red-400"}`}
                                style={{ width: `${barW}%` }}
                              />
                            </div>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            }
          />
        </div>
      )}

      {/* 機種別テーブル */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
          <span className="font-medium text-gray-700 text-sm">機種別詳細（{models.length}機種）</span>
          <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
            {(["all", "AT", "A", "BT"] as const).map(t => (
              <button
                key={t}
                onClick={() => setTypeFilter(t)}
                className={`px-3 py-1 rounded text-xs font-bold transition-colors ${
                  typeFilter === t
                    ? t === "A" ? "bg-green-600 text-white"
                    : t === "BT" ? "bg-purple-600 text-white"
                    : t === "AT" ? "bg-blue-600 text-white"
                    : "bg-white text-gray-700 shadow-sm"
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                {t === "all" ? "全機種" : t === "A" ? "Aタイプ" : t + "機"}
              </button>
            ))}
          </div>
        </div>
        <ResponsiveTable
          loading={false}
          empty={models.length === 0}
          emptyLabel="該当機種なし"
          mobile={models.map(m => {
            const weekMap = Object.fromEntries(m.weekly.map(w => [w.week, w]));
            return (
              <div key={m.model_name} className="px-4 py-3">
                <div className="flex items-center gap-2 min-w-0">
                  <span className={`text-xs font-bold px-1.5 py-0.5 rounded shrink-0 ${TYPE_COLOR[m.machine_type]}`}>
                    {TYPE_LABEL[m.machine_type]}
                  </span>
                  <span className="font-medium text-gray-800 text-sm truncate">{m.model_name}</span>
                </div>
                <div className="flex items-center gap-3 mt-1.5 text-xs text-gray-500">
                  <span className="whitespace-nowrap">{m.intro_date}</span>
                  <span>
                    {m.total_days <= 28
                      ? <span className="text-amber-600 font-medium">{m.total_days}日</span>
                      : `${m.total_days}日`}
                  </span>
                  <WrCell value={m.overall_win_rate} />
                  <span className="font-mono"><DiffCell value={m.overall_avg_diff} /></span>
                </div>
                <div className="flex gap-1.5 mt-2 overflow-x-auto pb-0.5">
                  {WEEKS.map(w => {
                    const wd = weekMap[w];
                    if (!wd) return null;
                    const bg =
                      wd.avg_diff >= 200 ? "bg-green-100" :
                      wd.avg_diff >= 0 ? "bg-yellow-50" :
                      "bg-red-50";
                    return (
                      <div key={w} className={`shrink-0 rounded px-2 py-1 text-center text-[10px] ${bg}`}>
                        <div className="text-gray-400">{w === 8 ? "8w〜" : `${w}w`}</div>
                        <div className="font-mono font-medium"><DiffCell value={wd.avg_diff} /></div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
          desktop={
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-[#1A3A5C] text-white text-xs">
                  <th className="px-4 py-3 text-left">機種名</th>
                  <th className="px-4 py-3 text-center whitespace-nowrap">導入日</th>
                  <th className="px-4 py-3 text-center whitespace-nowrap">経過日</th>
                  <th className="px-4 py-3 text-center whitespace-nowrap">全体勝率</th>
                  <th className="px-4 py-3 text-center whitespace-nowrap">全体平均差枚</th>
                  {WEEKS.map(w => (
                    <th key={w} className="px-3 py-3 text-center whitespace-nowrap">
                      {w === 8 ? "8w〜" : `${w}w`}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {models.map(m => {
                  const weekMap = Object.fromEntries(m.weekly.map(w => [w.week, w]));
                  return (
                    <tr key={m.model_name} className="hover:bg-gray-50">
                      <td className="px-4 py-2.5">
                        <div className="flex items-center gap-2">
                          <span className={`text-xs font-bold px-1.5 py-0.5 rounded shrink-0 ${TYPE_COLOR[m.machine_type]}`}>
                            {TYPE_LABEL[m.machine_type]}
                          </span>
                          <span className="font-medium text-gray-800 text-xs">{m.model_name}</span>
                        </div>
                      </td>
                      <td className="px-4 py-2.5 text-center text-xs text-gray-500 whitespace-nowrap">{m.intro_date}</td>
                      <td className="px-4 py-2.5 text-center text-xs text-gray-500">
                        {m.total_days <= 28
                          ? <span className="text-amber-600 font-medium">{m.total_days}日</span>
                          : `${m.total_days}日`}
                      </td>
                      <td className="px-4 py-2.5 text-center"><WrCell value={m.overall_win_rate} /></td>
                      <td className="px-4 py-2.5 text-center font-mono text-xs"><DiffCell value={m.overall_avg_diff} /></td>
                      {WEEKS.map(w => (
                        <WeekBadge key={w} wk={w} data={weekMap[w]} />
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          }
        />
        <div className="px-5 py-2 text-xs text-gray-400 border-t border-gray-100">
          各セル: 上段=平均差枚 / 下段=勝率。黄色ハイライト行=導入28日以内の現役新台
        </div>
      </div>
    </div>
  );
}
