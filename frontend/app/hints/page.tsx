"use client";

import { useEffect, useRef, useState } from "react";
import axios from "axios";
import { API } from "../lib/api";
import PageHeader from "../components/PageHeader";

interface Hints {
  date: string;
  store_post: string;
  cocochi: string;
  openchat: string;
  saved_at: string | null;
  has_store_images: boolean;
  has_cocochi_images: boolean;
}

function useImageList(initial: string[] = []) {
  const [images, setImages] = useState<string[]>(initial);

  const addFile = (file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const dataUrl = e.target?.result as string;
      setImages((prev) => [...prev, dataUrl]);
    };
    reader.readAsDataURL(file);
  };

  const remove = (i: number) => setImages((prev) => prev.filter((_, idx) => idx !== i));

  return { images, setImages, addFile, remove };
}

export default function HintsPage() {
  const [storePost, setStorePost] = useState("");
  const [cocochi, setCocochi] = useState("");
  const [openchat, setOpenchat] = useState("");
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const storeImgs = useImageList();
  const cococoImgs = useImageList();

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
        store_images: storeImgs.images,
        cocochi_images: cococoImgs.images,
      });
      setSavedAt(r.data.saved_at);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } finally {
      setSaving(false);
    }
  };

  const hasContent = storePost || cocochi || openchat || storeImgs.images.length > 0 || cococoImgs.images.length > 0;

  return (
    <div className="max-w-2xl mx-auto space-y-5">
      <PageHeader
        title="今日の示唆入力"
        description="ウスイ店長X・ococoichi・LINEオープンチャットの内容を貼り付け。ナナに自動反映されます。"
      />

      {savedAt && (
        <div className="flex items-center gap-2 text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg px-4 py-2">
          <span className="font-bold">保存済み</span>
          <span className="text-green-500">{savedAt}</span>
        </div>
      )}

      <div className="space-y-4">
        {/* ウスイ店長 */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 space-y-3">
          <div className="flex items-center gap-2">
            <span className="font-bold text-sm text-gray-800">ウスイ店長のXポスト</span>
            <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-red-100 text-red-700">最優先</span>
          </div>
          <ImageDropZone
            images={storeImgs.images}
            onAdd={storeImgs.addFile}
            onRemove={storeImgs.remove}
          />
          <textarea
            value={storePost}
            onChange={(e) => setStorePost(e.target.value)}
            onPaste={(e) => {
              const hasImage = Array.from(e.clipboardData.items).some((i) => i.type.startsWith("image/"));
              if (hasImage) {
                e.preventDefault();
                Array.from(e.clipboardData.items).forEach((item) => {
                  if (item.type.startsWith("image/")) { const f = item.getAsFile(); if (f) storeImgs.addFile(f); }
                });
              }
            }}
            placeholder={"投稿日時ごとコピペ（例）\n7月6日 8:23 AM\n今日も頑張っていきましょう🎯\n\n→ ナナが日時を見て当日示唆か前日結果かを自動判定します\n画像コピー中にここでCtrl+Vすると画像として追加されます"}
            rows={3}
            className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand/30 resize-y text-gray-700 placeholder-gray-300"
          />
        </div>

        {/* ococoichi */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 space-y-3">
          <div className="flex items-center gap-2">
            <span className="font-bold text-sm text-gray-800">ococoichi のXポスト</span>
            <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-orange-100 text-orange-700">解釈補助</span>
          </div>
          <ImageDropZone
            images={cococoImgs.images}
            onAdd={cococoImgs.addFile}
            onRemove={cococoImgs.remove}
          />
          <textarea
            value={cocochi}
            onChange={(e) => setCocochi(e.target.value)}
            onPaste={(e) => {
              const hasImage = Array.from(e.clipboardData.items).some((i) => i.type.startsWith("image/"));
              if (hasImage) {
                e.preventDefault();
                Array.from(e.clipboardData.items).forEach((item) => {
                  if (item.type.startsWith("image/")) { const f = item.getAsFile(); if (f) cococoImgs.addFile(f); }
                });
              }
            }}
            placeholder={"投稿日時ごとコピペ\n夜ポストは答え合わせ、朝ポストは示唆補助としてナナが解釈します\n画像コピー中にここでCtrl+Vすると画像として追加されます"}
            rows={3}
            className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand/30 resize-y text-gray-700 placeholder-gray-300"
          />
        </div>

        {/* LINE */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 space-y-2">
          <div className="flex items-center gap-2">
            <span className="font-bold text-sm text-gray-800">LINEオープンチャット</span>
            <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">トレンド補完</span>
          </div>
          <textarea
            value={openchat}
            onChange={(e) => setOpenchat(e.target.value)}
            placeholder="当月まとめや直近の傾向コメントをコピペ"
            rows={3}
            className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand/30 resize-y text-gray-700 placeholder-gray-300"
          />
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={save}
          disabled={saving || !hasContent}
          className="bg-brand text-white px-8 py-2.5 rounded-lg font-bold text-sm hover:bg-brand-light disabled:opacity-40 transition-colors"
        >
          {saving ? "保存中..." : "保存してナナに反映"}
        </button>
        {saved && <span className="text-green-600 text-sm font-medium">反映しました</span>}
        {hasContent && (
          <button
            onClick={() => {
              setStorePost(""); setCocochi(""); setOpenchat("");
              storeImgs.setImages([]); cococoImgs.setImages([]);
            }}
            className="text-gray-400 text-sm hover:text-gray-600"
          >
            クリア
          </button>
        )}
      </div>
    </div>
  );
}

function ImageDropZone({
  images,
  onAdd,
  onRemove,
}: {
  images: string[];
  onAdd: (f: File) => void;
  onRemove: (i: number) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handleFiles = (files: FileList | null) => {
    if (!files) return;
    Array.from(files).forEach((f) => {
      if (f.type.startsWith("image/")) onAdd(f);
    });
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    const items = e.clipboardData.items;
    for (const item of Array.from(items)) {
      if (item.type.startsWith("image/")) {
        const file = item.getAsFile();
        if (file) onAdd(file);
      }
    }
  };

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => { e.preventDefault(); setDragging(false); handleFiles(e.dataTransfer.files); }}
      onPaste={handlePaste}
      tabIndex={0}
      className={`rounded-lg border-2 border-dashed transition-colors cursor-pointer outline-none focus:ring-2 focus:ring-brand/30 ${
        dragging ? "border-brand bg-blue-50" : "border-gray-200 bg-gray-50"
      }`}
      onClick={() => inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        multiple
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />

      {images.length === 0 ? (
        <div className="py-4 text-center text-xs text-gray-400 select-none">
          クリック / ドラッグ＆ドロップ / Ctrl+V で画像を追加
        </div>
      ) : (
        <div className="p-2 flex flex-wrap gap-2" onClick={(e) => e.stopPropagation()}>
          {images.map((src, i) => (
            <div key={i} className="relative group">
              <img src={src} alt="" className="h-20 w-auto rounded border border-gray-200 object-cover" />
              <button
                onClick={() => onRemove(i)}
                className="absolute -top-1.5 -right-1.5 bg-red-500 text-white rounded-full w-4 h-4 text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity leading-none"
              >
                ×
              </button>
            </div>
          ))}
          <div
            className="h-20 w-16 flex items-center justify-center rounded border-2 border-dashed border-gray-300 text-gray-400 text-xs cursor-pointer hover:border-brand hover:text-brand transition-colors"
            onClick={() => inputRef.current?.click()}
          >
            ＋
          </div>
        </div>
      )}
    </div>
  );
}
