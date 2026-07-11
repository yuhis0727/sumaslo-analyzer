"use client";

import { useState } from "react";
import axios from "axios";
import { API } from "../lib/api";
import { diffStr } from "../lib/format";
import { MachineType, TypeBadge } from "../components/Badges";
import PageHeader from "../components/PageHeader";

type Rec = {
  priority: number;
  machine_number: number;
  model_name: string;
  machine_type: MachineType;
  win_rate: number;
  avg_diff: number;
  n_days: number;
  reason: string;
  tags: string[];
  is_fixed6: boolean;
  is_small_model: boolean;
};

type Result = {
  number: number;
  total: number;
  percentile: number;
  tier: "良番" | "中番" | "悪番";
  today: string;
  day_label: string;
  event_n: number;
  today_events: string[];
  strategy: string;
  data_basis: string;
  dow_label: string;
  dow_pattern: string;
  dow_hint: string;
  recommendations: Rec[];
};

const TIER_STYLE = {
  良番: { bg: "bg-green-500", text: "text-green-700", light: "bg-green-50 border-green-200" },
  中番: { bg: "bg-yellow-400", text: "text-yellow-700", light: "bg-yellow-50 border-yellow-200" },
  悪番: { bg: "bg-red-500", text: "text-red-700", light: "bg-red-50 border-red-200" },
};

export default function SimulatorPage() {
  const [number, setNumber] = useState("");
  const [total, setTotal] = useState("200");
  const [result, setResult] = useState<Result | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const run = async () => {
    const n = parseInt(number);
    const t = parseInt(total);
    if (!n || n < 1) { setError("番号を入力してください"); return; }
    if (n > t) { setError(`番号が参加者数(${t})を超えています`); return; }
    setError("");
    setLoading(true);
    setSaved(false);
    try {
      const r = await axios.get<Result>(`${API}/api/simulator/recommend`, {
        params: { number: n, total: t },
      });
      setResult(r.data);
    } catch {
      setError("データ取得エラー");
    } finally {
      setLoading(false);
    }
  };

  const savePrediction = async () => {
    if (!result) return;
    setSaving(true);
    try {
      await axios.post(`${API}/api/predictions`, {
        number: result.number,
        total: result.total,
        tier: result.tier,
        day_label: result.day_label,
        event_n: result.event_n,
        recommendations: result.recommendations,
      });
      setSaved(true);
    } catch {
      setError("予測の保存に失敗しました");
    } finally {
      setSaving(false);
    }
  };

  const tier = result ? TIER_STYLE[result.tier] : null;

  return (
    <div className="max-w-2xl mx-auto space-y-5">
      <PageHeader title="入場番号シミュレーター" description="番号を入れると狙い台ランキングを即出力" />

      {/* 入力 */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 space-y-4">
        <div className="flex gap-4 items-end">
          <div className="flex-1">
            <label className="block text-xs text-gray-500 mb-1">推定参加者数</label>
            <input
              type="number"
              value={total}
              onChange={e => setTotal(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30"
              placeholder="200"
            />
          </div>
          <div className="flex-[2]">
            <label className="block text-xs text-gray-500 mb-1">あなたの番号</label>
            <input
              type="number"
              value={number}
              onChange={e => setNumber(e.target.value)}
              onKeyDown={e => e.key === "Enter" && run()}
              className="w-full border-2 border-brand rounded-lg px-4 py-3 text-2xl font-bold text-center focus:outline-none focus:ring-2 focus:ring-brand/30"
              placeholder="—"
              autoFocus
            />
          </div>
          <button
            onClick={run}
            disabled={loading}
            className="bg-brand text-white px-6 py-3 rounded-lg font-bold text-sm hover:bg-brand-light disabled:opacity-40 transition-colors whitespace-nowrap"
          >
            {loading ? "..." : "判定"}
          </button>
        </div>
        {error && <p className="text-red-500 text-sm">{error}</p>}
      </div>

      {/* 結果 */}
      {result && tier && (
        <div className="space-y-4">
          {/* 判定バナー */}
          <div className={`rounded-xl border p-5 ${tier.light}`}>
            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
              <div className="flex items-center gap-4">
                <div className={`${tier.bg} text-white text-3xl font-black px-6 py-3 rounded-xl`}>
                  {result.tier}
                </div>
                <div>
                  <div className="text-lg font-bold text-gray-800">
                    {result.number}番 / {result.total}人中
                    <span className={`ml-2 text-sm font-normal ${tier.text}`}>
                      上位 {result.percentile.toFixed(0)}%
                    </span>
                  </div>
                  <div className="text-sm text-gray-500 mt-0.5">
                    {result.day_label}のデータ基準
                    {result.today_events.length > 0 && (
                      <span className="ml-2 bg-orange-100 text-orange-700 text-xs px-2 py-0.5 rounded-full">
                        {result.today_events.join("・")}
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <button
                onClick={savePrediction}
                disabled={saving || saved}
                className={`shrink-0 px-4 py-2 rounded-lg text-sm font-bold transition-colors whitespace-nowrap ${
                  saved
                    ? "bg-green-100 text-green-700"
                    : "bg-brand text-white hover:bg-brand-light disabled:opacity-40"
                }`}
              >
                {saved ? "保存済み" : saving ? "保存中..." : "この予測を保存"}
              </button>
            </div>
            <p className="mt-3 text-sm text-gray-700 leading-relaxed">{result.strategy}</p>
          </div>

          {/* 曜日仕掛け */}
          <div className="bg-indigo-50 border border-indigo-200 rounded-xl px-5 py-3 flex items-start gap-3">
            <div className="shrink-0 bg-indigo-600 text-white text-xs font-black px-2 py-1 rounded">
              {result.dow_label}曜
            </div>
            <div>
              <span className="font-bold text-indigo-800 text-sm">{result.dow_pattern}</span>
              <p className="text-xs text-indigo-600 mt-0.5">{result.dow_hint}</p>
            </div>
          </div>

          {/* 狙い台ランキング */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="px-5 py-3 border-b border-gray-100">
              <span className="font-bold text-gray-800">狙い台ランキング</span>
              <span className="text-xs text-gray-400 ml-2">{result.data_basis}</span>
            </div>
            <div className="divide-y divide-gray-50">
              {result.recommendations.map((rec) => (
                <div key={rec.machine_number} className={`px-5 py-4 flex items-start gap-4 ${rec.is_fixed6 ? "bg-amber-50/40" : ""}`}>
                  {/* 順位 */}
                  <div className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-black ${
                    rec.priority === 1 ? "bg-yellow-400 text-white" :
                    rec.priority === 2 ? "bg-gray-300 text-white" :
                    rec.priority === 3 ? "bg-amber-600 text-white" :
                    "bg-gray-100 text-gray-500"
                  }`}>
                    {rec.priority}
                  </div>

                  {/* 台情報 */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-lg font-black text-brand">{rec.machine_number}番</span>
                      <TypeBadge type={rec.machine_type} />
                      {rec.tags.map(t => (
                        <span key={t} className="text-xs bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded font-medium">
                          {t}
                        </span>
                      ))}
                    </div>
                    <div className="text-sm text-gray-700 mt-0.5 truncate">{rec.model_name}</div>
                    <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                      <span className={rec.avg_diff >= 0 ? "text-green-700 font-bold" : "text-red-500 font-bold"}>
                        平均 {diffStr(rec.avg_diff)}枚
                      </span>
                      <span>勝率 {Math.round(rec.win_rate * 100)}%</span>
                      <span>{rec.n_days}回分</span>
                      <span className="text-gray-400">{rec.reason}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
