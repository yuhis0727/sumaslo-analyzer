"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import EventOrNSelector, { FilterMode, EventName } from "../../components/EventOrNSelector";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

type ModelRow = {
  model_name: string;
  machine_type: "AT" | "A" | "BT";
  current_count: number;
  scale: "small" | "medium" | "large";
  n_days: number;
  avg_ratio: number;
  median_ratio: number;
  full_rate: number;
  avg_positive: number;
  pattern: string;
};

type Response = {
  small: ModelRow[];
  medium: ModelRow[];
  large: ModelRow[];
};

const PATTERN_STYLE: Record<string, string> = {
  "全台系濃厚":   "bg-green-100 text-green-800 border-green-300",
  "1/2集中寄り":  "bg-blue-100 text-blue-800 border-blue-300",
  "一部高設定":   "bg-yellow-100 text-yellow-800 border-yellow-300",
  "回収傾向":     "bg-gray-100 text-gray-500 border-gray-300",
};

const TYPE_STYLE: Record<string, string> = {
  AT: "bg-blue-50 text-blue-700",
  A:  "bg-green-50 text-green-700",
  BT: "bg-purple-50 text-purple-700",
};

function RatioBar({ ratio }: { ratio: number }) {
  const pct = Math.round(ratio * 100);
  const color =
    pct >= 75 ? "bg-green-500" :
    pct >= 55 ? "bg-blue-400" :
    pct >= 40 ? "bg-yellow-400" : "bg-gray-300";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-bold w-8 text-right">{pct}%</span>
    </div>
  );
}

function Section({ title, badge, badgeColor, rows, emptyText }: {
  title: string;
  badge: string;
  badgeColor: string;
  rows: ModelRow[];
  emptyText: string;
}) {
  if (rows.length === 0) return null;
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="px-5 py-3 border-b border-gray-100 flex items-center gap-2">
        <span className="font-bold text-gray-800">{title}</span>
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${badgeColor}`}>{badge}</span>
        <span className="text-xs text-gray-400 ml-auto">{rows.length}機種</span>
      </div>
      {rows.length === 0 ? (
        <p className="text-center py-8 text-sm text-gray-400">{emptyText}</p>
      ) : (
        <div className="divide-y divide-gray-50">
          {rows.map((r) => (
            <div key={r.model_name} className="px-5 py-3 grid grid-cols-[1fr_auto] gap-3 items-center">
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <span className="font-bold text-sm text-gray-800 truncate">{r.model_name}</span>
                  <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${TYPE_STYLE[r.machine_type]}`}>
                    {r.machine_type === "A" ? "Aタイプ" : r.machine_type + "機"}
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${PATTERN_STYLE[r.pattern]}`}>
                    {r.pattern}
                  </span>
                </div>
                <RatioBar ratio={r.avg_ratio} />
                <div className="flex gap-4 mt-1 text-xs text-gray-400">
                  <span>{r.current_count}台設置</span>
                  <span>平均 <strong className="text-gray-700">{r.avg_positive.toFixed(1)}台</strong>プラス</span>
                  {r.full_rate >= 0.1 && (
                    <span>全台系率 <strong className="text-green-700">{Math.round(r.full_rate * 100)}%</strong></span>
                  )}
                  <span>{r.n_days}日分</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function AllocationPage() {
  const [mode, setMode] = useState<FilterMode>("n");
  const [n, setN] = useState(7);
  const [event, setEvent] = useState<EventName>("ニャンギラス");
  const [data, setData] = useState<Response | null>(null);
  const [loading, setLoading] = useState(false);

  const buildParams = (m: FilterMode, nVal: number, ev: EventName) => {
    const p = new URLSearchParams({ min_days: "3" });
    if (m === "n") p.set("n", String(nVal));
    else if (m === "event") p.set("event", ev);
    else if (m === "plain") p.set("plain", "true");
    else p.set("all_days", "true");
    return p.toString();
  };

  const load = (m: FilterMode, nVal: number, ev: EventName) => {
    setLoading(true);
    axios.get<Response>(`${API}/api/data/allocation?${buildParams(m, nVal, ev)}`)
      .then((r) => setData(r.data))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(mode, n, event); }, []);

  const handleMode = (m: FilterMode) => { setMode(m); load(m, n, event); };
  const handleN = (v: number) => { setN(v); load(mode, v, event); };
  const handleEvent = (e: EventName) => { setEvent(e); load(mode, n, e); };

  const modeLabel =
    mode === "n" ? `${n}の日` :
    mode === "event" ? event :
    mode === "plain" ? "平常日" : "全期間";

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">台数規模別 高配分予測</h1>
          <p className="text-xs text-gray-400 mt-0.5">機種ごとに「この日種で何割の台がプラスになるか」の傾向を出す</p>
        </div>
        <EventOrNSelector
          mode={mode} n={n} event={event}
          onModeChange={handleMode} onNChange={handleN} onEventChange={handleEvent}
        />
      </div>

      {loading && (
        <div className="text-center py-12 text-gray-400 text-sm">集計中...</div>
      )}

      {data && !loading && (
        <div className="space-y-4">
          <div className="bg-indigo-50 border border-indigo-200 rounded-xl px-5 py-3 text-sm text-indigo-700">
            <strong>{modeLabel}</strong>のデータ基準。各機種の過去実績から「今日どの規模の機種に入りやすいか」を確認できます。
          </div>

          <Section
            title="少数台（4台以下）"
            badge="全台系コストが低い"
            badgeColor="bg-green-100 text-green-700 border-green-300"
            rows={data.small}
            emptyText="該当機種なし"
          />
          <Section
            title="中規模台（5〜12台）"
            badge="1/2集中が主流"
            badgeColor="bg-blue-100 text-blue-700 border-blue-300"
            rows={data.medium}
            emptyText="該当機種なし"
          />
          <Section
            title="大規模台（13台以上）"
            badge="列・一部高設定"
            badgeColor="bg-gray-100 text-gray-600 border-gray-300"
            rows={data.large}
            emptyText="該当機種なし"
          />
        </div>
      )}
    </div>
  );
}
