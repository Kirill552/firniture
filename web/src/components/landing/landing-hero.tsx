'use client';

import React from 'react';
import Link from 'next/link';
import { LANDING_COPY } from './landing-copy';
import { DraftingSheet } from './drafting-sheet';

/**
 * Первый экран: слева оффер и один CTA, справа — готовый чертёжный лист.
 * Асимметрия, крупная типографика, ступенчатое появление при загрузке.
 * H1 и описание — из LANDING_COPY (проверяются тестами копирайта).
 */
export function LandingHero() {
  const { heroOverline, h1, heroDescription, ctaPrimary, ctaHint } = LANDING_COPY;

  return (
    <div className="grid grid-cols-1 items-center gap-x-14 gap-y-12 pb-16 pt-14 lg:grid-cols-12 lg:pb-24 lg:pt-20">
      {/* Левая колонка */}
      <div className="lg:col-span-6">
        <div
          data-rise
          style={{ animationDelay: '0.05s' }}
          className="mb-6 inline-flex items-center gap-3 border border-[#b3a88f] bg-[#fbf8f1]/60 px-3 py-1.5"
        >
          <span className="h-2 w-2 bg-[#d8352a]" />
          <span className="font-tech text-[11px] uppercase tracking-[1.5px] text-[#544c3f]">
            {heroOverline}
          </span>
        </div>

        <h1
          data-rise
          style={{ animationDelay: '0.14s' }}
          className="font-display mb-7 max-w-[15ch] text-[46px] font-extrabold leading-[0.94] tracking-[-2px] text-[#17130d] sm:text-[58px] xl:text-[68px]"
        >
          {h1}
        </h1>

        <p
          data-rise
          style={{ animationDelay: '0.24s' }}
          className="mb-9 max-w-[46ch] text-[18px] leading-[1.55] text-[#544c3f]"
        >
          {heroDescription}
        </p>

        <div data-rise style={{ animationDelay: '0.34s' }}>
          <Link
            href="/new"
            className="group inline-flex h-14 w-fit items-center gap-3 bg-[#d8352a] px-8 text-[17px] font-semibold text-white transition-all hover:-translate-y-0.5 hover:bg-[#c22e24] hover:shadow-[6px_6px_0_#17130d] active:translate-y-0 active:shadow-none"
          >
            {ctaPrimary}
            <span className="transition-transform group-hover:translate-x-1">→</span>
          </Link>
          <p className="mt-4 flex max-w-[52ch] items-start gap-2.5 text-[13px] leading-snug text-[#8c8373]">
            <span className="mt-1.5 h-px w-6 shrink-0 bg-[#d8352a]" />
            {ctaHint}
          </p>
        </div>
      </div>

      {/* Правая колонка — чертёжный лист */}
      <div data-rise style={{ animationDelay: '0.3s' }} className="lg:col-span-6">
        <div className="hardline hardshadow relative bg-[#fbf8f1] p-2.5">
          <DraftingSheet stage={2} progress={1} hero />
          {/* «Луч сканирования» поверх листа как знак распознавания */}
          <div className="pointer-events-none absolute inset-2.5 overflow-hidden">
            <div className="scan-sweep h-full w-16 bg-gradient-to-r from-transparent via-[#d8352a]/12 to-transparent" />
          </div>
        </div>
        <div className="mt-4 flex items-center justify-between">
          <span className="font-tech flex items-center gap-2.5 text-[11px] uppercase tracking-[1px] text-[#8c8373]">
            <span className="h-px w-7 bg-[#d8352a]" /> вход: один эскиз или PDF
          </span>
          <span className="font-tech text-[11px] uppercase tracking-[1px] text-[#8c8373]">
            .jpg · .png · .pdf
          </span>
        </div>
      </div>
    </div>
  );
}
