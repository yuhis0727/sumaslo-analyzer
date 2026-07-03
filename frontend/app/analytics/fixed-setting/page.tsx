"use client";

import { useEffect, useState } from "react";
import axios from "axios";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

type FixedSix = {
  machine_number: number;
  model_name: string;
  win_rate_vs_model: number;
  avg_diff: number;
  model_avg_diff: number;
  avg_day_deviation: number;
  consecutive_beat: number;
  n_days: number;
};

const N_LABELS = [null, 1, 2, 3, 4, 5, 6, 7, 8, 9] as const;

export default function FixedSettingPage() {
  const [data, setData] = useState<FixedSix[]>([]);
  const [n, setN] = useState<number | null>(7);
  const [minDays, setMinDays] = useState(8);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = async (nVal: number | null, md: number) => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({ min_days: String(md) });
      if (nVal !== null) params.set("n", String(nVal));
      const res = await axios.get<FixedSix[]>(`${API}/api/data/fixed-setting?${params}`);
      setData(res.data);
    } catch {
      setError("APIエラー: バックエンドを確認してください");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(n, minDays); }, []);

  const handleN = (v: number | null) => { setN(v); load(v, minDays); };
  const handleMinDays = (v: number) => { setMinDays(v); load(n, v); };

  const winColor = (r: number) =>
    r >= 0.7 ? "bg-green-100 text-green-700" :
    r >= 0.5 ? "bg-yellow-100 text-yellow-700" :
    "bg-gray-100 text-gray-500";

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">固定設定6台検出</h1>
        <p className="text-sm text-gray-500 mt-1">
          全台系日のノイズを除いた「日ごとの偏差」で本当に強い台を検出します
        </p>
      </div>

      <div className="flex flex-wrap gap-4 items-center">
        <div className="flex gap-1 items-center flex-wrap">
          <span className="text-sm text-gray-600 mr-1">Nの日:</span>
          {N_LABELS.map((v) => (
            <button
              key={v ?? "all"}
              onClick={() => handleN(v)}
              className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                n === v
                  ? "bg-[#1A3A5C] text-white"
                  : "bg-white border border-gray-300 text-gray-700 hover:bg-gray-50"
              }`}
            >
              {v === null ? "全日" : `${v}の日`}
            </button>
          ))}
        </div>

        <div className="flex gap-1 items-center">
          <span className="text-sm text-gray-600 mr-1">最低回数:</span>
          {[5, 8, 10, 15].map((d) => (
            <button
              key={d}
              onClick={() => handleMinDays(d)}
              className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                minDays === d
                  ? "bg-indigo-600 text-white"
                  : "bg-white border border-gray-300 text-gray-700 hover:bg-gray-50"
              }`}
            >
              {d}回以上
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-3 text-sm">{error}</div>
      )}

      <div className="bg-white rounded-xl shadow-sm border border-gray-200">
        <div className="p-4 border-b border-gray-100">
          <span className="font-semibold text-gray-700">
            {loading ? "読み込み中..." : `${data.length}台が候補`}
          </span>
          <span className="text-xs text-gray-400 ml-2">
            {n !== null ? `${n}の日限定` : "全日程"} / 日ごと偏差+1000枚以上 / 連続3回以上機種平均超え
          </span>
        </div>

        {data.length === 0 && !loading ? (
          <div className="p-8 text-center text-gray-400 text-sm">
            条件に合う台がありません。閾値を下げるか、対象日を変更してください。
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-600 text-xs uppercase tracking-wide">
                <tr>
                  <th className="px-4 py-3 text-left">台番</th>
                  <th className="px-4 py-3 text-left">機種名</th>
                  <th className="px-4 py-3 text-right" title="機種平均を上回った日の割合（全台系日除外済）">
                    対機種勝率
                  </th>
                  <th className="px-4 py-3 text-right">平均差枚</th>
                  <th className="px-4 py-3 text-right" title="日ごとの(この台 - 機種平均)の平均。全台系日は偏差≈0になるため自動除外">
                    平均偏差
                  </th>
                  <th className="px-4 py-3 text-right" title="直近N回連続で機種平均を超えた回数">
                    連続超え
                  </th>
                  <th className="px-4 py-3 text-right">回数</th>
                </tr>
              </thead>
              <tbody>
                {data.map((row, i) => (
                  <tr key={row.machine_number} className="border-t border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {i < 3 && (
                          <span className={`text-xs font-bold w-5 h-5 rounded-full flex items-center justify-center ${
                            i === 0 ? "bg-yellow-400 text-white" :
                            i === 1 ? "bg-gray-300 text-gray-700" :
                            "bg-amber-600 text-white"
                          }`}>{i + 1}</span>
                        )}
                        <span className="font-mono font-bold text-[#1A3A5C]">{row.machine_number}番</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-700 max-w-[200px] truncate">{row.model_name}</td>
                    <td className="px-4 py-3 text-right">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-bold ${winColor(row.win_rate_vs_model)}`}>
                        {(row.win_rate_vs_model * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td className={`px-4 py-3 text-right font-mono font-medium ${
                      row.avg_diff >= 0 ? "text-green-600" : "text-red-500"
                    }`}>
                      {row.avg_diff >= 0 ? "+" : ""}{row.avg_diff.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="text-green-700 font-semibold">
                        +{row.avg_day_deviation.toLocaleString()}
                      </span>
                      <span className="text-xs text-gray-400 ml-1">枚</span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className={`font-bold ${
                        row.consecutive_beat >= 5 ? "text-green-600" :
                        row.consecutive_beat >= 3 ? "text-yellow-600" : "text-gray-500"
                      }`}>
                        {row.consecutive_beat}連続
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-gray-500">{row.n_days}回</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-800 space-y-1">
        <p className="font-semibold">検出基準（全台系ノイズ除去済）:</p>
        <ul className="list-disc list-inside space-y-0.5 text-blue-700">
          <li><strong>日ごとの偏差</strong> = その台の差枚 − 同日の機種平均差枚</li>
          <li>全台系日は機種全体が底上げされるため偏差 ≈ 0 → 自動的にノイズ除去</li>
          <li>平均偏差が <strong>+1000枚以上</strong>、かつ直近 <strong>3回連続で機種平均超え</strong></li>
        </ul>
      </div>
    </div>
  );
}
