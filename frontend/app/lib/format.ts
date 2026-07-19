/** 差枚数の表示用フォーマッタ・色ユーティリティ（全ページ共通） */

export const diffStr = (v: number) => `${v >= 0 ? "+" : ""}${v.toLocaleString()}`;

export const diffColor = (v: number) => (v >= 0 ? "text-green-600" : "text-red-500");
