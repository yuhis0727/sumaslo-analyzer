'use client';
import { ReactNode, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import './globals.css';

/** 当日の立ち回り（入場〜着席の意思決定に使うページ） */
const PRIMARY = [
  { href: '/simulator', label: '🎰 番号判定' },
  { href: '/hints', label: '📋 示唆入力' },
  { href: '/ai', label: '💬 ナナ' },
  { href: '/', label: 'ダッシュボード' },
];

/** 分析・データ確認（事前準備・検証に使うページ） */
const ANALYSIS = [
  { href: '/predictions', label: '予測履歴' },
  { href: '/machines', label: '台番分析' },
  { href: '/models', label: '機種別分析' },
  { href: '/analytics/allocation', label: '高配分予測' },
  { href: '/analytics/zentai', label: '全台系パターン' },
  { href: '/analytics/events', label: 'イベント別分析' },
  { href: '/analytics/fixed-setting', label: '固定設定6検出' },
  { href: '/analytics/layout-changes', label: '配置変更' },
  { href: '/analytics/new-machines', label: '新台分析' },
];

export default function Layout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // ページ遷移でメニューを閉じる
  useEffect(() => {
    setDropdownOpen(false);
    setMobileOpen(false);
  }, [pathname]);

  // ドロップダウン外クリックで閉じる
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener('click', onClick);
    return () => document.removeEventListener('click', onClick);
  }, []);

  const isActive = (href: string) =>
    href === '/' ? pathname === '/' : pathname === href || pathname.startsWith(`${href}/`);
  const analysisActive = ANALYSIS.some((item) => isActive(item.href));

  return (
    <html lang="ja">
      <head>
        <title>マルハン蒲田7 分析</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body className="bg-gray-50 min-h-screen">
        <nav className="bg-brand text-white shadow-lg sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 flex items-center h-12">
            <Link href="/" className="font-bold text-base mr-6 whitespace-nowrap">
              🎰 蒲田7分析
            </Link>

            {/* デスクトップナビ */}
            <div className="hidden md:flex items-center gap-1 flex-1">
              {PRIMARY.map(({ href, label }) => (
                <Link
                  key={href}
                  href={href}
                  className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                    isActive(href) ? 'bg-white text-brand' : 'hover:bg-white/20'
                  }`}
                >
                  {label}
                </Link>
              ))}

              <div className="relative ml-1" ref={dropdownRef}>
                <button
                  onClick={() => setDropdownOpen((v) => !v)}
                  className={`px-3 py-1 rounded text-sm font-medium transition-colors flex items-center gap-1 ${
                    analysisActive ? 'bg-white text-brand' : 'hover:bg-white/20'
                  }`}
                >
                  📊 分析
                  <span className={`text-xs transition-transform ${dropdownOpen ? 'rotate-180' : ''}`}>▾</span>
                </button>
                {dropdownOpen && (
                  <div className="absolute left-0 top-full mt-1 w-48 bg-white rounded-lg shadow-xl border border-gray-200 py-1 overflow-hidden">
                    {ANALYSIS.map(({ href, label }) => (
                      <Link
                        key={href}
                        href={href}
                        className={`block px-4 py-2 text-sm transition-colors ${
                          isActive(href)
                            ? 'bg-brand/10 text-brand font-bold'
                            : 'text-gray-700 hover:bg-gray-50'
                        }`}
                      >
                        {label}
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* モバイル: ハンバーガー */}
            <button
              onClick={() => setMobileOpen((v) => !v)}
              className="md:hidden ml-auto p-2 rounded hover:bg-white/20"
              aria-label="メニュー"
            >
              <span className="block w-5 space-y-1">
                <span className="block h-0.5 bg-white" />
                <span className="block h-0.5 bg-white" />
                <span className="block h-0.5 bg-white" />
              </span>
            </button>
          </div>

          {/* モバイルメニュー */}
          {mobileOpen && (
            <div className="md:hidden border-t border-white/20 px-4 py-3 space-y-1 bg-brand">
              <p className="text-xs text-white/50 font-bold px-2 pt-1">当日の立ち回り</p>
              {PRIMARY.map(({ href, label }) => (
                <Link
                  key={href}
                  href={href}
                  className={`block px-2 py-1.5 rounded text-sm font-medium ${
                    isActive(href) ? 'bg-white text-brand' : 'hover:bg-white/20'
                  }`}
                >
                  {label}
                </Link>
              ))}
              <p className="text-xs text-white/50 font-bold px-2 pt-2">分析</p>
              {ANALYSIS.map(({ href, label }) => (
                <Link
                  key={href}
                  href={href}
                  className={`block px-2 py-1.5 rounded text-sm font-medium ${
                    isActive(href) ? 'bg-white text-brand' : 'hover:bg-white/20'
                  }`}
                >
                  {label}
                </Link>
              ))}
            </div>
          )}
        </nav>
        <main className="max-w-7xl mx-auto px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
