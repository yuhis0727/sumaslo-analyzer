'use client';
import { ReactNode } from 'react';

import Head from './head';
import './globals.css';

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <html lang="ja" suppressHydrationWarning={true}>
      <Head />
      <body>
        <main>
          {children}
        </main>
      </body>
    </html>
  );
}
