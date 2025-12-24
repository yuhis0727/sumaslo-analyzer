"use client";

import { useState, useEffect } from "react";

interface Store {
  id: number;
  name: string;
  area: string | null;
  anaslo_url: string | null;
}

interface AnalysisResult {
  store_name: string;
  high_setting_probability: number;
  confidence_score: number;
  recommended_machines: number[];
  analysis_details: {
    statistical_analysis: {
      average_game_count: number;
      average_difference: number;
      positive_machines_count: number;
      high_performers: Array<{
        machine_number: number;
        model_name: string;
        total_difference: number;
      }>;
    };
    total_machines: number;
    analysis_date: string;
  };
}

export default function AnalysisPage() {
  const [stores, setStores] = useState<Store[]>([]);
  const [selectedStore, setSelectedStore] = useState<number | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(
    null
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://api.f2t.dev";

  useEffect(() => {
    fetchStores();
  }, []);

  const fetchStores = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/slots/stores`);
      if (!response.ok) throw new Error("店舗の取得に失敗しました");
      const data = await response.json();
      setStores(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "エラーが発生しました");
    }
  };

  const analyzeStore = async (storeId: number) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/slots/analyze/${storeId}`,
        {
          method: "POST",
        }
      );
      if (!response.ok) throw new Error("分析に失敗しました");
      const data = await response.json();
      setAnalysisResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "エラーが発生しました");
    } finally {
      setLoading(false);
    }
  };

  const getProbabilityColor = (probability: number): string => {
    if (probability >= 0.7) return "text-green-600";
    if (probability >= 0.4) return "text-yellow-600";
    return "text-red-600";
  };

  const getProbabilityBgColor = (probability: number): string => {
    if (probability >= 0.7) return "bg-green-100";
    if (probability >= 0.4) return "bg-yellow-100";
    return "bg-red-100";
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-8">
      <div className="max-w-6xl mx-auto">
        <div className="bg-white rounded-lg shadow-xl p-8 mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            スマスロ AI 分析システム
          </h1>
          <p className="text-gray-600">
            AIが店舗データを分析して高設定台の可能性を予測します
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-bold text-gray-800 mb-4">店舗選択</h2>
            {stores.length === 0 ? (
              <p className="text-gray-500">店舗が登録されていません</p>
            ) : (
              <div className="space-y-2">
                {stores.map((store) => (
                  <button
                    key={store.id}
                    onClick={() => {
                      setSelectedStore(store.id);
                      analyzeStore(store.id);
                    }}
                    className={`w-full text-left p-4 rounded-lg transition-all ${
                      selectedStore === store.id
                        ? "bg-blue-500 text-white shadow-md"
                        : "bg-gray-100 hover:bg-gray-200 text-gray-800"
                    }`}
                  >
                    <div className="font-semibold">{store.name}</div>
                    {store.area && (
                      <div className="text-sm opacity-80">{store.area}</div>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="md:col-span-2">
            {loading && (
              <div className="bg-white rounded-lg shadow-lg p-8 text-center">
                <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-500 mx-auto mb-4"></div>
                <p className="text-gray-600">分析中...</p>
              </div>
            )}

            {error && (
              <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg">
                {error}
              </div>
            )}

            {!loading && !error && analysisResult && (
              <div className="space-y-6">
                <div className="bg-white rounded-lg shadow-lg p-6">
                  <h2 className="text-2xl font-bold text-gray-800 mb-4">
                    {analysisResult.store_name} - 分析結果
                  </h2>

                  <div
                    className={`p-6 rounded-lg mb-6 ${getProbabilityBgColor(
                      analysisResult.high_setting_probability
                    )}`}
                  >
                    <div className="text-center">
                      <div className="text-sm text-gray-600 mb-2">
                        高設定台の確率
                      </div>
                      <div
                        className={`text-5xl font-bold ${getProbabilityColor(
                          analysisResult.high_setting_probability
                        )}`}
                      >
                        {(analysisResult.high_setting_probability * 100).toFixed(
                          1
                        )}
                        %
                      </div>
                      <div className="mt-4 text-sm text-gray-600">
                        信頼度スコア:{" "}
                        {(analysisResult.confidence_score * 100).toFixed(1)}%
                      </div>
                    </div>
                  </div>

                  {analysisResult.recommended_machines.length > 0 && (
                    <div className="mb-6">
                      <h3 className="text-xl font-semibold text-gray-800 mb-3">
                        おすすめ台番号
                      </h3>
                      <div className="flex flex-wrap gap-2">
                        {analysisResult.recommended_machines.map((num) => (
                          <span
                            key={num}
                            className="bg-blue-500 text-white px-4 py-2 rounded-full font-semibold"
                          >
                            {num}番台
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                <div className="bg-white rounded-lg shadow-lg p-6">
                  <h3 className="text-xl font-semibold text-gray-800 mb-4">
                    統計分析
                  </h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <div className="text-sm text-gray-600">平均ゲーム数</div>
                      <div className="text-2xl font-bold text-gray-800">
                        {analysisResult.analysis_details.statistical_analysis.average_game_count.toFixed(
                          0
                        )}
                        G
                      </div>
                    </div>
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <div className="text-sm text-gray-600">平均差枚数</div>
                      <div className="text-2xl font-bold text-gray-800">
                        {analysisResult.analysis_details.statistical_analysis.average_difference.toFixed(
                          0
                        )}
                        枚
                      </div>
                    </div>
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <div className="text-sm text-gray-600">プラス台数</div>
                      <div className="text-2xl font-bold text-gray-800">
                        {
                          analysisResult.analysis_details.statistical_analysis
                            .positive_machines_count
                        }
                        台
                      </div>
                    </div>
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <div className="text-sm text-gray-600">総台数</div>
                      <div className="text-2xl font-bold text-gray-800">
                        {analysisResult.analysis_details.total_machines}台
                      </div>
                    </div>
                  </div>
                </div>

                {analysisResult.analysis_details.statistical_analysis
                  .high_performers.length > 0 && (
                  <div className="bg-white rounded-lg shadow-lg p-6">
                    <h3 className="text-xl font-semibold text-gray-800 mb-4">
                      高パフォーマンス台 TOP5
                    </h3>
                    <div className="overflow-x-auto">
                      <table className="min-w-full">
                        <thead className="bg-gray-100">
                          <tr>
                            <th className="px-4 py-2 text-left">台番号</th>
                            <th className="px-4 py-2 text-left">機種名</th>
                            <th className="px-4 py-2 text-right">差枚数</th>
                          </tr>
                        </thead>
                        <tbody>
                          {analysisResult.analysis_details.statistical_analysis.high_performers.map(
                            (machine, idx) => (
                              <tr
                                key={idx}
                                className="border-t hover:bg-gray-50"
                              >
                                <td className="px-4 py-2 font-semibold">
                                  {machine.machine_number}
                                </td>
                                <td className="px-4 py-2">
                                  {machine.model_name}
                                </td>
                                <td className="px-4 py-2 text-right font-bold text-green-600">
                                  +{machine.total_difference}枚
                                </td>
                              </tr>
                            )
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}

            {!loading && !error && !analysisResult && (
              <div className="bg-white rounded-lg shadow-lg p-12 text-center">
                <div className="text-gray-400 mb-4">
                  <svg
                    className="w-24 h-24 mx-auto"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                    />
                  </svg>
                </div>
                <p className="text-gray-600 text-lg">
                  左側の店舗を選択して分析を開始してください
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
