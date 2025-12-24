"use client";

const Page = () => {
  return (
    <div className="w-4/5 mx-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">お知らせ</h2>
        <div className="border-y border-gray-200 py-4 mb-6 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="text-gray-400">
              <span className="block text-sm">2025.1.11</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="bg-green-100 text-green-600 text-xs font-medium px-3 py-1 rounded-full">
                重要
              </span>
              <img
                src="/images/logo.png"
                alt="logo"
                className="h-10 w-10"
              />
            </div>
            <div className="text-gray-900 font-semibold text-lg">
              FAST-FULLSTACK-TEMPLATE sample
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Page;
