"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import axios from "axios";
import Link from "next/link";
import { MachineType, TypeBadge, WinBadge } from "../../components/Badges";
import { API } from "../../lib/api";
import { diffStr, diffColor } from "../../lib/format";

type Monthly = { month: string; avg_diff: number; win_rate: number };
type MachineStat = { machine_number: number; n_days: number; win_rate: number; avg_diff: number; total_diff: number };

type Detail = {
  model_name: string;
  machine_type: MachineType;
  machine_count: number;
  overall: { win_rate: number; avg_diff: number; total_diff: number };
  monthly: Monthly[];
  machines: MachineStat[];
};

export default function ModelDetailPage() {
  const { name } = useParams<{ name: string }>();
  const modelName = decodeURIComponent(name);
  const [data, setData] = useState<Detail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get<Detail>(`${API}/api/data/model/${encodeURIComponent(modelName)}`)
      .then(r => setData(r.data))
      .finally(() => setLoading(false));
  }, [modelName]);

  if (loading) return <div className="py-16 text-center text-gray-400">読み込み中...</div>;
  if (!data) return <div className="py-16 text-center text-red-500">機種が見つかりません</div>;

  const maxAbsDiff = Math.max(...data.monthly.map(m => Math.abs(m.avg_diff)), 1);

  return (
    <div className="space-y-6">
      {/* ヘッダー */}
      <div className="flex items-start gap-4">
        <Link href="/models" className="text-gray-400 hover:text-gray-600 mt-1">← 機種一覧</Link>
        <div>
          <div className="flex items-center gap-3">
            <div className="text-2xl font-bold text-gray-900">{data.model_name}</div>
            <TypeBadge type={data.machine_type} />
          </div>
          <div className="text-sm text-gray-500 mt-0.5">{data.machine_count}台設置</div>
        </div>
      </div>

      {/* サマリーカード */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {[
          { label: "全体勝率", value: <WinBadge rate={data.overall.win_rate} /> },
          { label: "全体平均差枚", value: <span className={`text-xl font-bold ${diffColor(data.overall.avg_diff)}`}>{diffStr(data.overall.avg_diff)}</span> },
          { label: "全台累計差枚", value: <span className={`text-xl font-bold ${diffColor(data.overall.total_diff)}`}>{diffStr(data.overall.total_diff)}</span> },
        ].map(c => (
          <div key={c.label} className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-xs text-gray-500 mb-1">{c.label}</div>
            {c.value}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* 月別バーチャート */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="font-semibold text-gray-700 mb-4">月別平均差枚（機種全体）</h2>
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

        {/* 台番別ランキング */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="font-semibold text-gray-700 mb-3">台番別ランキング</h2>
          <div className="overflow-y-auto max-h-72">
            <table className="w-full text-sm">
              <thead className="text-xs text-gray-500 sticky top-0 bg-white">
                <tr>
                  <th className="text-left pb-2">#</th>
                  <th className="text-left pb-2">台番</th>
                  <th className="text-right pb-2">勝率</th>
                  <th className="text-right pb-2">平均差枚</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {data.machines.map((m, i) => (
                  <tr key={m.machine_number} className="hover:bg-gray-50">
                    <td className="py-1.5 text-gray-400 text-xs">{i + 1}</td>
                    <td className="py-1.5">
                      <Link href={`/machines/${m.machine_number}`} className="font-mono font-bold text-brand hover:underline">
                        {m.machine_number}番
                      </Link>
                    </td>
                    <td className="py-1.5 text-right"><WinBadge rate={m.win_rate} /></td>
                    <td className={`py-1.5 text-right font-mono font-medium ${diffColor(m.avg_diff)}`}>{diffStr(m.avg_diff)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
