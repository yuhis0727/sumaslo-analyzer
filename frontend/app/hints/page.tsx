"use client";

import { useEffect, useState } from "react";
import axios from "axios";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

type Hints = {
  date: string;
  store_post: string;
  cocochi: string;
  openchat: string;
  saved_at: string | null;
};

export default function HintsPage() {
  const [storePost, setStorePost] = useState("");
  const [cocochi, setCocochi] = useState("");
  const [openchat, setOpenchat] = useState("");
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    axios.get<Hints>(`${API}/api/hints/today`).then((r) => {
      setStorePost(r.data.store_post);
      setCocochi(r.data.cocochi);
      setOpenchat(r.data.openchat);
      setSavedAt(r.data.saved_at);
    });
  }, []);

  const save = async () => {
    setSaving(true);
    setSaved(false);
    try {
      const r = await axios.post<Hints>(`${API}/api/hints/today`, {
        store_post: storePost,
        cocochi,
        openchat,
      });
      setSavedAt(r.data.saved_at);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } finally {
      setSaving(false);
    }
  };

  const hasContent = storePost || cocochi || openchat;

  return (
    <div className="max-w-2xl mx-auto space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">今日の示唆入力</h1>
        <p className="text-sm text-gray-500 mt-1">
          ウスイ店長X・ococoichi・LINEオープンチャットの内容をコピペ。ナナと番号シミュレーターに反映されます。
        </p>
      </div>

      {savedAt && (
        <div className="flex items-center gap-2 text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg px-4 py-2">
          <span className="font-bold">保存済み</span>
          <span className="text-green-500">{savedAt}</span>
        </div>
      )}

      <div className="space-y-4">
        <Section
          label="ウスイ店長のXポスト"
          badge="最優先"
          badgeColor="bg-red-100 text-red-700"
          placeholder={"投稿日時ごとコピペ（例）\n7月6日 8:23 AM\n今日も頑張っていきましょう🎯\n\n→ ナナが日時を見て当日示唆か前日結果かを自動判定します"}
          value={storePost}
          onChange={setStorePost}
        />

        <Section
          label="ococoichi のXポスト"
          badge="解釈補助"
          badgeColor="bg-orange-100 text-orange-700"
          placeholder={"投稿日時ごとコピペ\n夜ポストは答え合わせ、朝ポストは示唆補助としてナナが解釈します"}
          value={cocochi}
          onChange={setCocochi}
        />

        <Section
          label="LINEオープンチャット"
          badge="トレンド補完"
          badgeColor="bg-blue-100 text-blue-700"
          placeholder="当月まとめや直近の傾向コメントをコピペ"
          value={openchat}
          onChange={setOpenchat}
        />
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={save}
          disabled={saving || !hasContent}
          className="bg-[#1A3A5C] text-white px-8 py-2.5 rounded-lg font-bold text-sm hover:bg-[#2a5a8c] disabled:opacity-40 transition-colors"
        >
          {saving ? "保存中..." : "保存してナナに反映"}
        </button>
        {saved && (
          <span className="text-green-600 text-sm font-medium">反映しました</span>
        )}
        {hasContent && (
          <button
            onClick={() => { setStorePost(""); setCocochi(""); setOpenchat(""); }}
            className="text-gray-400 text-sm hover:text-gray-600"
          >
            クリア
          </button>
        )}
      </div>

      {!hasContent && !savedAt && (
        <p className="text-xs text-gray-400">
          今日の示唆情報はまだ入力されていません。
        </p>
      )}
    </div>
  );
}

function Section({
  label, badge, badgeColor, placeholder, value, onChange,
}: {
  label: string;
  badge: string;
  badgeColor: string;
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 space-y-2">
      <div className="flex items-center gap-2">
        <span className="font-bold text-sm text-gray-800">{label}</span>
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${badgeColor}`}>{badge}</span>
      </div>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={4}
        className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-[#1A3A5C]/30 resize-y text-gray-700 placeholder-gray-300"
      />
    </div>
  );
}
