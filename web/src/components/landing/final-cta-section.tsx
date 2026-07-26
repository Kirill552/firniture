import React from 'react';
import Link from 'next/link';
import { LANDING_COPY } from './landing-copy';

/**
 * Финальный CTA перед подвалом. Копирайт — из LANDING_COPY (проверен тестами).
 */
export function FinalCtaSection() {
  return (
    <div className="flex flex-col items-start gap-6 md:flex-row md:items-center md:justify-between">
      <div>
        <div className="mb-3 font-mono text-[10px] uppercase tracking-[2px] text-[#66707a]">
          Первый заказ
        </div>
        <h2 className="max-w-[22ch] text-[28px] md:text-[36px] font-extrabold leading-[0.98] tracking-[-1px] text-[#171a1d]">
          {LANDING_COPY.finalCtaTitle}
        </h2>
        <p className="mt-4 max-w-[46ch] text-[15px] leading-relaxed text-[#66707a]">
          {LANDING_COPY.finalCtaHint}
        </p>
      </div>
      <Link
        href="/new"
        className="inline-flex items-center gap-2 rounded-xl bg-[#171a1d] px-7 py-4 text-[15px] font-bold text-white transition-all duration-200 hover:-translate-y-0.5 hover:bg-black"
      >
        {LANDING_COPY.ctaPrimary}
        <span aria-hidden>→</span>
      </Link>
    </div>
  );
}
