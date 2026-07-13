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
    <header className="sticky top-0 z-50 border-b-2 border-[#17130d] bg-[#ece4d5]/95 backdrop-blur-sm">
      <div className="mx-auto flex h-[68px] max-w-[1280px] items-center justify-between px-6">
        <Link href="/" className="group flex items-center gap-3">
          <span className="relative flex h-9 w-9 items-center justify-center border-2 border-[#17130d] bg-[#fbf8f1]">
            <span className="font-display text-[15px] font-extrabold tracking-[-1px] text-[#17130d]">АР</span>
            <span className="absolute -right-[3px] -top-[3px] h-2 w-2 bg-[#d8352a]" />
          </span>
          <span className="flex flex-col leading-none">
            <span className="font-display text-[19px] font-bold tracking-[-0.6px] text-[#17130d]">{brand}</span>
            <span className="font-tech mt-0.5 text-[9px] uppercase tracking-[1.5px] text-[#8c8373]">
              обмер · спецификация · DXF
            </span>
          </span>
        </Link>

        <nav className="flex items-center gap-1 sm:gap-2">
          <a
            href="#how"
            className="font-tech hidden px-3 py-2 text-[13px] uppercase tracking-[0.5px] text-[#544c3f] transition-colors hover:text-[#d8352a] sm:inline-block"
          >
            {navHow}
          </a>
          <a
            href="#capabilities"
            className="font-tech hidden px-3 py-2 text-[13px] uppercase tracking-[0.5px] text-[#544c3f] transition-colors hover:text-[#d8352a] sm:inline-block"
          >
            {navCapabilities}
          </a>
          <Link
            href="/login"
            className="font-tech ml-1 border-2 border-[#17130d] bg-[#fbf8f1] px-4 py-2 text-[13px] uppercase tracking-[0.5px] text-[#17130d] transition-all hover:-translate-y-0.5 hover:shadow-[3px_3px_0_#17130d]"
          >
            {navLogin}
          </Link>
        </nav>
      </div>
    </header>
  );
}
