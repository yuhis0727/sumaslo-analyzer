"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import EventOrNSelector, { FilterMode, EventName } from "../../components/EventOrNSelector";
import { RankBadge } from "../../components/Badges";
import PageHeader from "../../components/PageHeader";
import { ResponsiveTable } from "../../components/ResponsiveTable";
import { API } from "../../lib/api";
import { diffStr, diffColor } from "../../lib/format";

interface ModelScore {
  model_name: string;
  machine_count: number;
  total_event_days: number;
  zentai_count: number;
  zentai_rate: number;
  avg_zentai_diff: number;
  avg_all_diff: number;
  recent_zentai_3: number;
  score: number;
}

interface ZentaiHistory {
  date: string;
  event_n: number;
  model_name: string;
  total_machines: number;
  plus_machines: number;
  positive_rate: number;
  avg_diff: number;
}

type Tab = "score" | "history";

export default function ZentaiPage() {
  const [tab, setTab] = useState<Tab>("score");
  const [mode, setMode] = useState<FilterMode>("n");
  const [n, setN] = useState(7);
  const [event, setEvent] = useState<EventName>("ニャンギラス");
  const [scores, setScores] = useState<ModelScore[]>([]);
  const [history, setHistory] = useState<ZentaiHistory[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = async (m: FilterMode, nVal: number, ev: EventName) => {
    setLoading(true);
    setError("");
    try {
      const p = m === "n" ? `n=${nVal}` : `event=${encodeURIComponent(ev)}`;
      const [scoreRes, histRes] = await Promise.all([
        axios.get<ModelScore[]>(`${API}/api/data/model-score?${p}&min_event_days=3`),
        axios.get<ZentaiHistory[]>(`${API}/api/data/zentai-history?${p}`),
      ]);
      setScores(scoreRes.data);
      setHistory(histRes.data);
    } catch {
      setError("APIエラー: バックエンドを確認してください");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(mode, n, event); }, []);

  const handleMode = (m: FilterMode) => { setMode(m); load(m, n, event); };
  const handleN = (v: number) => { setN(v); load(mode, v, event); };
  const handleEvent = (e: EventName) => { setEvent(e); load(mode, n, e); };

  const recentBadge = (cnt: number) => {
    if (cnt === 3) return <span className="inline-block px-2 py-0.5 rounded-full text-xs font-bold bg-red-100 text-red-700">直近3連続</span>;
    if (cnt === 2) return <span className="inline-block px-2 py-0.5 rounded-full text-xs font-bold bg-orange-100 text-orange-700">直近2/3</span>;
    if (cnt === 1) return <span className="inline-block px-2 py-0.5 rounded-full text-xs font-bold bg-yellow-100 text-yellow-700">直近1/3</span>;
    return <span className="inline-block px-2 py-0.5 rounded-full text-xs font-bold bg-gray-100 text-gray-400">直近なし</span>;
  };

  const scoreBar = (score: number, max: number) => {
    const pct = Math.min((score / max) * 100, 100);
    return (
      <div className="flex items-center gap-2">
        <div className="flex-1 bg-gray-100 rounded-full h-2">
          <div
            className="h-2 rounded-full bg-gradient-to-r from-blue-400 to-indigo-600"
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="text-xs font-mono text-gray-600 w-14 text-right">{score.toFixed(0)}</span>
      </div>
    );
  };

  const maxScore = scores[0]?.score ?? 1;

  return (
    <div className="space-y-5">
      <PageHeader
        title="全台系パターン検知"
        description="機種内プラス台65%以上の日を全台系と判定し、頻度と期待値をスコア化します"
      />

      <EventOrNSelector
        mode={mode} n={n} event={event}
        onModeChange={handleMode} onNChange={handleN} onEventChange={handleEvent}
      />

      {/* タブ */}
      <div className="flex gap-0 border-b border-gray-200">
        {(["score", "history"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-5 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t
                ? "border-brand text-brand"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t === "score" ? "期待度スコア" : "過去実績"}
          </button>
        ))}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-3 text-sm">{error}</div>
      )}

      {/* 期待度スコアタブ */}
      {tab === "score" && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="p-4 border-b border-gray-100">
            <span className="font-semibold text-gray-700">
              {loading ? "読み込み中..." : `${scores.length}機種`}
            </span>
            <span className="text-xs text-gray-400 ml-2">
              スコア = 全台系頻度 × 全台系時の平均差枚
            </span>
          </div>
          <ResponsiveTable
            loading={false}
            empty={scores.length === 0}
            mobile={scores.map((row, i) => (
              <div key={row.model_name} className="px-4 py-3">
                <div className="flex items-center gap-2 min-w-0">
                  <RankBadge rank={i + 1} />
                  <span className="font-medium text-gray-800 truncate">{row.model_name}</span>
                </div>
                <div className="flex items-center justify-between gap-2 mt-1.5">
                  <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-bold ${
                    row.zentai_rate >= 0.5 ? "bg-green-100 text-green-700" :
                    row.zentai_rate >= 0.3 ? "bg-yellow-100 text-yellow-700" :
                    "bg-gray-100 text-gray-500"
                  }`}>
                    {(row.zentai_rate * 100).toFixed(0)}%
                    <span className="ml-1 font-normal opacity-70">({row.zentai_count}/{row.total_event_days})</span>
                  </span>
                  {recentBadge(row.recent_zentai_3)}
                </div>
                <div className="flex items-center justify-between gap-2 mt-1.5 text-xs text-gray-500">
                  <span>{row.machine_count}台</span>
                  <span className={`font-mono font-medium ${diffColor(row.avg_zentai_diff)}`}>{diffStr(row.avg_zentai_diff)}</span>
                </div>
                <div className="mt-1.5">{scoreBar(row.score, maxScore)}</div>
              </div>
            ))}
            desktop={
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-gray-600 text-xs uppercase tracking-wide">
                  <tr>
                    <th className="px-4 py-3 text-left">機種名</th>
                    <th className="px-4 py-3 text-right">台数</th>
                    <th className="px-4 py-3 text-right">全台系率</th>
                    <th className="px-4 py-3 text-right">全台系時平均</th>
                    <th className="px-4 py-3 text-right">直近3回</th>
                    <th className="px-4 py-3 text-left w-48">期待度スコア</th>
                  </tr>
                </thead>
                <tbody>
                  {scores.map((row, i) => (
                    <tr key={row.model_name} className="border-t border-gray-100 hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <RankBadge rank={i + 1} />
                          <span className="font-medium text-gray-800 truncate max-w-[220px]">{row.model_name}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right text-gray-500">{row.machine_count}台</td>
                      <td className="px-4 py-3 text-right">
                        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-bold ${
                          row.zentai_rate >= 0.5 ? "bg-green-100 text-green-700" :
                          row.zentai_rate >= 0.3 ? "bg-yellow-100 text-yellow-700" :
                          "bg-gray-100 text-gray-500"
                        }`}>
                          {(row.zentai_rate * 100).toFixed(0)}%
                          <span className="ml-1 font-normal opacity-70">({row.zentai_count}/{row.total_event_days})</span>
                        </span>
                      </td>
                      <td className={`px-4 py-3 text-right font-mono font-medium ${diffColor(row.avg_zentai_diff)}`}>
                        {diffStr(row.avg_zentai_diff)}
                      </td>
                      <td className="px-4 py-3 text-right">{recentBadge(row.recent_zentai_3)}</td>
                      <td className="px-4 py-3">{scoreBar(row.score, maxScore)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            }
          />
        </div>
      )}

      {/* 過去実績タブ */}
      {tab === "history" && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="p-4 border-b border-gray-100">
            <span className="font-semibold text-gray-700">
              {loading ? "読み込み中..." : `${history.length}件の全台系実績`}
            </span>
          </div>
          <ResponsiveTable
            loading={false}
            empty={history.length === 0}
            mobile={history.map((row, i) => (
              <div key={i} className="px-4 py-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-gray-600 text-sm">{row.date}</span>
                    <span className="inline-block w-6 h-6 rounded-full bg-brand text-white text-xs font-bold flex items-center justify-center">
                      {row.event_n}
                    </span>
                  </div>
                  <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-bold ${
                    row.positive_rate >= 0.8 ? "bg-green-100 text-green-700" :
                    "bg-yellow-100 text-yellow-700"
                  }`}>
                    {(row.positive_rate * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="flex items-center justify-between gap-2 mt-1.5 text-xs text-gray-500">
                  <span className="font-medium text-gray-800 truncate">{row.model_name}</span>
                  <span>{row.plus_machines}/{row.total_machines}台</span>
                </div>
                <div className={`mt-1 text-sm font-mono font-medium ${diffColor(row.avg_diff)}`}>{diffStr(row.avg_diff)}</div>
              </div>
            ))}
            desktop={
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-gray-600 text-xs uppercase tracking-wide">
                  <tr>
                    <th className="px-4 py-3 text-left">日付</th>
                    <th className="px-4 py-3 text-right">N</th>
                    <th className="px-4 py-3 text-left">機種名</th>
                    <th className="px-4 py-3 text-right">台数</th>
                    <th className="px-4 py-3 text-right">プラス率</th>
                    <th className="px-4 py-3 text-right">平均差枚</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((row, i) => (
                    <tr key={i} className="border-t border-gray-100 hover:bg-gray-50">
                      <td className="px-4 py-3 font-mono text-gray-600">{row.date}</td>
                      <td className="px-4 py-3 text-right">
                        <span className="inline-block w-7 h-7 rounded-full bg-brand text-white text-xs font-bold flex items-center justify-center">
                          {row.event_n}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-medium text-gray-800 max-w-[220px] truncate">{row.model_name}</td>
                      <td className="px-4 py-3 text-right text-gray-500">
                        {row.plus_machines}/{row.total_machines}台
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-bold ${
                          row.positive_rate >= 0.8 ? "bg-green-100 text-green-700" :
                          "bg-yellow-100 text-yellow-700"
                        }`}>
                          {(row.positive_rate * 100).toFixed(0)}%
                        </span>
                      </td>
                      <td className={`px-4 py-3 text-right font-mono font-medium ${diffColor(row.avg_diff)}`}>
                        {diffStr(row.avg_diff)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            }
          />
        </div>
      )}
    </div>
  );
}
