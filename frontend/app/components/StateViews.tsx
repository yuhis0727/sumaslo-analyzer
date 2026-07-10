/** ローディング・エラーの共通表示 */

export function LoadingState({ label = "読み込み中..." }: { label?: string }) {
  return (
    <div className="flex items-center justify-center py-16 text-gray-400">
      {label}
    </div>
  );
}

export function ErrorAlert({ message }: { message: string }) {
  return (
    <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-3 text-sm">
      {message}
    </div>
  );
}
