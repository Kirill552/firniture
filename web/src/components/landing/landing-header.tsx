'use client';

import React from 'react';
import Link from 'next/link';
import { LANDING_COPY } from './landing-copy';

/**
 * Шапка публичного лендинга в стиле чертёжного штампа.
 * Логотип — уголок-марка «АР» с красной засечкой. Один вход, без второго CTA.
 */
export function LandingHeader() {
  const { brand, navHow, navCapabilities, navLogin } = LANDING_COPY;

  return (
    <header className="sticky top-0 z-50 border-b border-[#d7dde2] bg-[#f3f6f8]/95 backdrop-blur-md">
      <div className="mx-auto flex h-[64px] max-w-[1280px] items-center justify-between px-6">
        <Link href="/" className="group flex items-center gap-3">
          <span className="relative flex h-8 w-8 items-center justify-center border border-[#d7dde2] bg-white rounded-lg">
            <span className="text-[14px] font-extrabold tracking-[-1px] text-[#171a1d]">АР</span>
            <span className="absolute -right-[2px] -top-[2px] h-2 w-2 rounded-full bg-[#c7ff00]" />
          </span>
          <span className="flex flex-col leading-none">
            <span className="text-[17px] font-bold tracking-[-0.6px] text-[#171a1d]">{brand}</span>
            <span className="font-mono mt-0.5 text-[8.5px] uppercase tracking-[1.5px] text-[#66707a]">
              обмер · спецификация · DXF
            </span>
          </span>
        </Link>

        <nav className="flex items-center gap-1 sm:gap-2">
          <a
            href="#how"
            className="font-mono hidden px-3 py-2 text-[12px] uppercase tracking-[0.5px] text-[#66707a] transition-colors hover:text-[#171a1d] sm:inline-block"
          >
            {navHow}
          </a>
          <a
            href="#capabilities"
            className="font-mono hidden px-3 py-2 text-[12px] uppercase tracking-[0.5px] text-[#66707a] transition-colors hover:text-[#171a1d] sm:inline-block"
          >
            {navCapabilities}
          </a>
          <Link
            href="/login"
            className="ml-1 border border-[#d7dde2] bg-white px-4 py-1.5 text-xs font-semibold text-[#171a1d] rounded-lg hover:bg-[#f3f6f8] active:scale-[0.98] transition-all duration-150 cursor-pointer"
          >
            {navLogin}
          </Link>
        </nav>
      </div>
    </header>
  );
}
