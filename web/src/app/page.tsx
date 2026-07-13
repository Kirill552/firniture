import React from 'react';
import Link from 'next/link';
import { Unbounded, Golos_Text, JetBrains_Mono } from 'next/font/google';
import { LandingHeader } from '@/components/landing/landing-header';
import { LandingHero } from '@/components/landing/landing-hero';
import { ProcessStory } from '@/components/landing/process-story';
import { OutputSection } from '@/components/landing/output-section';
import { LANDING_COPY } from '@/components/landing/landing-copy';

// Шрифты подключаются на маршруте лендинга (кириллица + латиница).
// Unbounded — акцентный дисплей, Golos Text — основной, JetBrains Mono — техтекст.
const display = Unbounded({ subsets: ['latin', 'cyrillic'], variable: '--font-display', display: 'swap' });
const golos = Golos_Text({ subsets: ['latin', 'cyrillic'], variable: '--font-golos', display: 'swap' });
const tech = JetBrains_Mono({ subsets: ['latin', 'cyrillic'], variable: '--font-tech', display: 'swap' });

const CAPS = [
  { n: '01', label: 'Размеры' },
  { n: '02', label: 'Уточнения' },
  { n: '03', label: 'Спецификация' },
  { n: '04', label: 'DXF + PDF' },
];

/**
 * Лендинг АвтоРаскрой — концепция «Чертёжная доска».
 * Приём: технический чертёж корпуса, который дорисовывается при прокрутке.
 * Весь смысл (оффер, 5 этапов, DXF/PDF, CTA) присутствует в HTML без JS.
 * Только SVG-графика — без WebGL, без лишних JS-чанков на мобильных.
 */
export default function LandingPage() {
  return (
    <div className={`landing-root ${display.variable} ${golos.variable} ${tech.variable} min-h-screen`}>
      <a href="#main" className="skip-link">
        Перейти к основному содержимому
      </a>

      <LandingHeader />

      <main id="main" tabIndex={-1}>
        {/* HERO */}
        <section className="mx-auto max-w-[1280px] px-6">
          <LandingHero />
        </section>

        {/* Полоса возможностей — техническая линейка */}
        <section id="capabilities" className="border-y-2 border-[#17130d] bg-[#fbf8f1]">
          <div className="mx-auto grid max-w-[1280px] grid-cols-2 md:grid-cols-4">
            {CAPS.map((c, i) => (
              <div
                key={c.n}
                className={`flex items-center gap-4 px-6 py-6 ${
                  i < CAPS.length - 1 ? 'md:border-r-2 md:border-[#cec4ae]' : ''
                } ${i < 2 ? 'border-b-2 border-[#cec4ae] md:border-b-0' : ''}`}
              >
                <span className="font-tech text-[13px] text-[#d8352a]">{c.n}</span>
                <span className="font-display text-[17px] font-semibold tracking-[-0.4px] text-[#17130d]">
                  {c.label}
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* SCROLL STORY — пять этапов, самозарисовывающийся чертёж */}
        <section id="how" className="mx-auto max-w-[1280px] px-6 pb-28 pt-24">
          <ProcessStory />
        </section>

        {/* РЕЗУЛЬТАТ */}
        <section className="border-t-2 border-[#17130d] bg-[#e3dac8]/40">
          <div className="mx-auto max-w-[1280px] px-6 py-20">
            <OutputSection />
          </div>
        </section>

        {/* ФИНАЛЬНЫЙ CTA — чертёжный лист во всю ширину */}
        <section className="mx-auto max-w-[1280px] px-6 py-24">
          <div className="hardline hardshadow relative overflow-hidden bg-[#fbf8f1] px-8 py-16 md:px-16">
            {/* Угловые метки */}
            <span className="absolute left-4 top-4 h-4 w-4 border-l-2 border-t-2 border-[#17130d]" />
            <span className="absolute right-4 top-4 h-4 w-4 border-r-2 border-t-2 border-[#17130d]" />
            <span className="absolute bottom-4 left-4 h-4 w-4 border-b-2 border-l-2 border-[#17130d]" />
            <span className="absolute bottom-4 right-4 h-4 w-4 border-b-2 border-r-2 border-[#17130d]" />

            <div className="max-w-[22ch]">
              <div className="mb-4 font-tech text-[12px] uppercase tracking-[2px] text-[#8c8373]">
                Лист · чистый
              </div>
              <h2 className="font-display text-[34px] font-extrabold leading-[1.02] tracking-[-1.2px] text-[#17130d] md:text-[44px]">
                {LANDING_COPY.finalCtaTitle}
              </h2>
              <Link
                href="/new"
                className="group mt-9 inline-flex h-14 w-fit items-center gap-3 bg-[#d8352a] px-9 text-[17px] font-semibold text-white transition-all hover:-translate-y-0.5 hover:bg-[#c22e24] hover:shadow-[6px_6px_0_#17130d] active:translate-y-0 active:shadow-none"
              >
                {LANDING_COPY.ctaPrimary}
                <span className="transition-transform group-hover:translate-x-1">→</span>
              </Link>
              <p className="mt-4 text-[13px] text-[#8c8373]">{LANDING_COPY.finalCtaHint}</p>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t-2 border-[#17130d] bg-[#fbf8f1]">
        <div className="mx-auto flex max-w-[1280px] flex-col items-start gap-4 px-6 py-8 sm:flex-row sm:items-center sm:justify-between">
          <div className="font-tech flex items-center gap-3 text-[12px] text-[#8c8373]">
            <span className="flex h-6 w-6 items-center justify-center border border-[#17130d] text-[10px] font-bold text-[#17130d]">
              АР
            </span>
            {LANDING_COPY.footerCopyright}
          </div>
          <div className="font-tech flex flex-wrap gap-x-6 gap-y-2 text-[12px] uppercase tracking-[0.5px]">
            <Link href="/pricing" className="text-[#544c3f] transition-colors hover:text-[#d8352a]">
              Тарифы
            </Link>
            <Link href="/login" className="text-[#544c3f] transition-colors hover:text-[#d8352a]">
              Войти
            </Link>
            <a
              href="mailto:support@avtoraskroy.ru"
              className="text-[#544c3f] transition-colors hover:text-[#d8352a]"
            >
              support@avtoraskroy.ru
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
