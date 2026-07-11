"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import { API } from "../lib/api";
import { diffStr } from "../lib/format";
import { MachineType, TypeBadge } from "../components/Badges";
import { LoadingState, ErrorAlert } from "../components/StateViews";
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
  actual_diff: number | null;
  hit: boolean | null;
};

type Entry = {
  id: string;
  date: string;
  saved_at: string;
  number: number;
  total: number;
  tier: "良番" | "中番" | "悪番";
  day_label: string;
  event_n: number;
  recommendations: Rec[];
  note: string;
  hit_rate: number | null;
  judged_count: number;
  total_count: number;
};

const TIER_STYLE: Record<Entry["tier"], string> = {
  良番: "bg-green-500",
  中番: "bg-yellow-400",
  悪番: "bg-red-500",
};

function HitBadge({ hit }: { hit: boolean | null }) {
  if (hit === null) return <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">判定待ち</span>;
  if (hit) return <span className="text-xs text-green-700 bg-green-100 px-2 py-0.5 rounded-full font-bold">的中</span>;
  return <span className="text-xs text-red-600 bg-red-50 px-2 py-0.5 rounded-full font-bold">外れ</span>;
}

function HitRateBadge({ rate, judged, total }: { rate: number | null; judged: number; total: number }) {
  if (rate === null) return <span className="text-xs text-gray-400">判定待ち（{total}台）</span>;
  const pct = Math.round(rate * 100);
  const color = pct >= 60 ? "bg-green-600 text-white" : pct >= 30 ? "bg-yellow-100 text-yellow-800" : "bg-gray-100 text-gray-600";
  return (
    <span className={`text-sm font-bold px-2.5 py-1 rounded-lg ${color}`}>
      的中率 {pct}%
      <span className="ml-1 font-normal opacity-80">({judged}/{total}台判定済)</span>
    </span>
  );
}

function NoteEditor({ entry, onSaved }: { entry: Entry; onSaved: (note: string) => void }) {
  const [note, setNote] = useState(entry.note);
  const [saving, setSaving] = useState(false);
  const dirty = note !== entry.note;

  const save = async () => {
    setSaving(true);
    try {
      await axios.patch(`${API}/api/predictions/${entry.date}/${entry.id}`, { note });
      onSaved(note);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mt-3">
      <label className="text-xs text-gray-500 mb-1 block">振り返りメモ（的中/外れの原因分析）</label>
      <div className="flex gap-2">
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="例: 店長ポストの示唆を見落とした／固定6候補が読み通り出た 等"
          rows={2}
          className="flex-1 text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand/30 resize-y text-gray-700 placeholder-gray-300"
        />
        <button
          onClick={save}
          disabled={!dirty || saving}
          className="shrink-0 self-start bg-gray-100 text-gray-700 px-3 py-2 rounded-lg text-xs font-bold hover:bg-gray-200 disabled:opacity-40 transition-colors"
        >
          {saving ? "保存中..." : "メモ保存"}
        </button>
      </div>
    </div>
  );
}

export default function PredictionsPage() {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    axios.get<Entry[]>(`${API}/api/predictions/history?limit=60`)
      .then((r) => setEntries(r.data))
      .catch(() => setError("予測履歴の取得に失敗しました"))
      .finally(() => setLoading(false));
  }, []);

  const judgedEntries = entries.filter((e) => e.hit_rate !== null);
  const overallRate = judgedEntries.length
    ? judgedEntries.reduce((s, e) => s + (e.hit_rate as number), 0) / judgedEntries.length
    : null;

  return (
    <div className="max-w-2xl mx-auto space-y-5">
      <PageHeader
        title="予測履歴"
        description="保存した予測を実績データと自動照合し、的中/外れを記録します"
      />

      {overallRate !== null && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 flex items-center justify-between">
          <span className="text-sm text-gray-500">直近{judgedEntries.length}件の平均的中率</span>
          <span className="text-2xl font-black text-brand">{Math.round(overallRate * 100)}%</span>
        </div>
      )}

      {loading && <LoadingState label="予測履歴を読み込み中..." />}
      {error && <ErrorAlert message={error} />}

      {!loading && !error && entries.length === 0 && (
        <div className="text-center py-16 text-gray-400 text-sm">
          まだ保存された予測がありません。シミュレーターの結果画面から保存できます。
        </div>
      )}

      <div className="space-y-4">
        {entries.map((entry) => (
          <div key={entry.id} className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <div className="flex items-center gap-2">
                <span className={`${TIER_STYLE[entry.tier]} text-white text-xs font-black px-2 py-1 rounded`}>
                  {entry.tier}
                </span>
                <span className="font-bold text-gray-800">{entry.date}</span>
                <span className="text-xs text-gray-400">{entry.day_label}</span>
              </div>
              <HitRateBadge rate={entry.hit_rate} judged={entry.judged_count} total={entry.total_count} />
            </div>

            <div className="text-xs text-gray-400 mt-1">
              {entry.number}番 / {entry.total}人中
            </div>

            <div className="mt-3 divide-y divide-gray-50">
              {entry.recommendations.map((rec) => (
                <div key={rec.machine_number} className="py-2 flex items-center justify-between gap-2">
                  <div className="min-w-0 flex items-center gap-2">
                    <span className="font-bold text-brand text-sm shrink-0">{rec.machine_number}番</span>
                    <TypeBadge type={rec.machine_type} short />
                    <span className="text-xs text-gray-600 truncate">{rec.model_name}</span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {rec.actual_diff !== null && (
                      <span className={`text-xs font-mono font-medium ${rec.actual_diff >= 0 ? "text-green-700" : "text-red-500"}`}>
                        {diffStr(rec.actual_diff)}枚
                      </span>
                    )}
                    <HitBadge hit={rec.hit} />
                  </div>
                </div>
              ))}
            </div>

            <NoteEditor
              entry={entry}
              onSaved={(note) => setEntries((prev) => prev.map((e) => (e.id === entry.id ? { ...e, note } : e)))}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
