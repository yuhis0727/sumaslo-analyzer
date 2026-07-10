import { ReactNode } from "react";
import { LoadingState } from "./StateViews";

/**
 * 一覧テーブルの共通レスポンシブラッパー。
 * スマホ幅ではカードリスト、md以上では従来のtableを出し分ける。
 */
export function ResponsiveTable({
  loading,
  empty,
  emptyLabel = "データなし",
  mobile,
  desktop,
}: {
  loading: boolean;
  empty: boolean;
  emptyLabel?: string;
  mobile: ReactNode;
  desktop: ReactNode;
}) {
  if (loading) return <LoadingState />;
  if (empty) return <div className="text-center py-12 text-gray-400 text-sm">{emptyLabel}</div>;
  return (
    <>
      <div className="md:hidden divide-y divide-gray-100">{mobile}</div>
      <div className="hidden md:block overflow-x-auto">{desktop}</div>
    </>
  );
}
