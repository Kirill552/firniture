import React from 'react';
import Link from 'next/link';
import {
  LANDING_COPY,
  FOOTER_COLUMNS,
  FOOTER_TAGLINE,
  FOOTER_EMAIL,
} from './landing-copy';
import { LEGAL } from '@/lib/legal';

/**
 * SEO-подвал лендинга: перелинковка разделов, документы, контакты.
 * Семантика: footer > nav[aria-label], ссылки только на существующие страницы.
 */
export function LandingFooter() {
  return (
    <div className="mx-auto max-w-[1280px] px-6 py-14">
      <div className="grid grid-cols-1 gap-10 md:grid-cols-12">
        <div className="md:col-span-5">
          <div className="text-[15px] font-extrabold tracking-[-0.5px] text-[#171a1d]">
            {LANDING_COPY.brand}
          </div>
          <p className="mt-3 max-w-[40ch] text-[13px] leading-relaxed text-[#66707a]">
            {FOOTER_TAGLINE}
          </p>
          <a
            href={`mailto:${FOOTER_EMAIL}`}
            className="mt-4 inline-block text-[13px] font-semibold text-[#171a1d] underline decoration-[#d7dde2] underline-offset-4 hover:decoration-[#171a1d]"
          >
            {FOOTER_EMAIL}
          </a>
        </div>

        {FOOTER_COLUMNS.map((col) => (
          <nav
            key={col.title}
            aria-label={`Подвал: ${col.title}`}
            className="md:col-span-3"
          >
            <div className="font-mono text-[10px] uppercase tracking-[2px] text-[#66707a]">
              {col.title}
            </div>
            <ul className="mt-4 space-y-2.5">
              {col.links.map((l) => (
                <li key={l.href}>
                  <Link
                    href={l.href}
                    className="text-[13px] text-[#66707a] transition-colors hover:text-[#171a1d]"
                  >
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        ))}

        <div className="md:col-span-1" />
      </div>

      <div className="mt-12 flex flex-col gap-3 border-t border-[#d7dde2] pt-6 text-[12px] text-[#66707a] md:flex-row md:items-center md:justify-between">
        <span>{LANDING_COPY.footerCopyright}</span>
        <span>{`${LEGAL.operatorForm.replace(/ \(.+\)/, '')} ${LEGAL.operatorName} · ИНН ${LEGAL.inn}`}</span>
      </div>
    </div>
  );
}
