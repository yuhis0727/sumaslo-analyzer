"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import { ResponsiveTable } from "../../components/ResponsiveTable";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

type LayoutChange = {
  machine_number: number;
  changed_date: string;
  prev_model: string;
  latest_model: string;
  days_since_change: number;
};

export default function LayoutChangesPage() {
  const [data, setData] = useState<LayoutChange[]>([]);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = async (d: number) => {
    setLoading(true);
    setError("");
    try {
      const res = await axios.get<LayoutChange[]>(`${API}/api/data/layout-changes?days=${d}`);
      setData(res.data);
    } catch {
      setError("APIエラー: バックエンドを確認してください");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(days); }, []);

  const handleDays = (d: number) => { setDays(d); load(d); };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">配置変更アラート</h1>
          <p className="text-sm text-gray-500 mt-1">機種名が変わった台番を検出します</p>
        </div>
        <div className="flex gap-2">
          {[14, 30, 60, 90].map((d) => (
            <button
              key={d}
              onClick={() => handleDays(d)}
              className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                days === d
                  ? "bg-[#1A3A5C] text-white"
                  : "bg-white border border-gray-300 text-gray-700 hover:bg-gray-50"
              }`}
            >
              直近{d}日
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-3 text-sm">{error}</div>
      )}

      <div className="bg-white rounded-xl shadow-sm border border-gray-200">
        <div className="p-4 border-b border-gray-100 flex items-center justify-between">
          <span className="font-semibold text-gray-700">
            {loading ? "読み込み中..." : `${data.length}件の配置変更`}
          </span>
          <span className="text-xs text-gray-400">直近{days}日間</span>
        </div>

        {data.length === 0 && !loading ? (
          <div className="p-8 text-center text-gray-400 text-sm">配置変更なし</div>
        ) : (
          <ResponsiveTable
            loading={false}
            empty={false}
            mobile={data.map((row) => (
              <div key={row.machine_number} className="px-4 py-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono font-bold text-brand">{row.machine_number}番</span>
                  <span
                    className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                      row.days_since_change <= 7
                        ? "bg-red-100 text-red-700"
                        : row.days_since_change <= 21
                        ? "bg-yellow-100 text-yellow-700"
                        : "bg-gray-100 text-gray-500"
                    }`}
                  >
                    {row.days_since_change}日前
                  </span>
                </div>
                <div className="text-xs text-gray-400 mt-1">{row.changed_date}</div>
                <div className="text-sm mt-1 flex items-center gap-1.5 flex-wrap">
                  <span className="text-red-600 line-through opacity-70">{row.prev_model}</span>
                  <span className="text-gray-300">→</span>
                  <span className="font-medium text-green-700">{row.latest_model}</span>
                </div>
              </div>
            ))}
            desktop={
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-gray-600 text-xs uppercase tracking-wide">
                  <tr>
                    <th className="px-4 py-3 text-left">台番</th>
                    <th className="px-4 py-3 text-left">変更日</th>
                    <th className="px-4 py-3 text-left">変更前</th>
                    <th className="px-4 py-3 text-left">変更後（現在）</th>
                    <th className="px-4 py-3 text-right">経過日数</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((row) => (
                    <tr key={row.machine_number} className="border-t border-gray-100 hover:bg-gray-50">
                      <td className="px-4 py-3 font-mono font-bold text-[#1A3A5C]">
                        {row.machine_number}番
                      </td>
                      <td className="px-4 py-3 text-gray-600">{row.changed_date}</td>
                      <td className="px-4 py-3 text-red-600 line-through opacity-70">
                        {row.prev_model}
                      </td>
                      <td className="px-4 py-3 font-medium text-green-700">
                        {row.latest_model}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span
                          className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                            row.days_since_change <= 7
                              ? "bg-red-100 text-red-700"
                              : row.days_since_change <= 21
                              ? "bg-yellow-100 text-yellow-700"
                              : "bg-gray-100 text-gray-500"
                          }`}
                        >
                          {row.days_since_change}日前
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            }
          />
        )}
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-800">
        <span className="font-semibold">注意:</span>{" "}
        配置変更台はデータが少なく、過去の勝率・差枚が現在の機種を反映していない可能性があります。
        新しい機種は台番別ランキングで過小評価されるため注意してください。
      </div>
    </div>
  );
}
