'use client';
import { ReactNode } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import './globals.css';

const NAV = [
  { href: '/',                      label: 'ダッシュボード' },
  { href: '/machines',              label: '台番分析' },
  { href: '/models',                label: '機種別' },
  { href: '/analytics/zentai',           label: '全台系' },
  { href: '/analytics/events',           label: 'イベント' },
  { href: '/analytics/layout-changes',  label: '配置変更' },
  { href: '/analytics/fixed-setting',   label: '固定設定6' },
  { href: '/analytics/new-machines',    label: '新台分析' },
  { href: '/ai',                    label: 'ナナ' },
];

export default function Layout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return (
    <html lang="ja">
      <head>
        <title>マルハン蒲田7 分析</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body className="bg-gray-50 min-h-screen">
        <nav className="bg-[#1A3A5C] text-white shadow-lg sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 flex items-center h-12">
            <span className="font-bold text-base mr-8 whitespace-nowrap">🎰 蒲田7分析</span>
            <div className="flex gap-1">
              {NAV.map(({ href, label }) => (
                <Link
                  key={href}
                  href={href}
                  className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                    pathname === href
                      ? 'bg-white text-[#1A3A5C]'
                      : 'hover:bg-white/20'
                  }`}
                >
                  {label}
                </Link>
              ))}
            </div>
          </div>
        </nav>
        <main className="max-w-7xl mx-auto px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
