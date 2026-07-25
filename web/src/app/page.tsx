import { LandingHeader } from '@/components/landing/landing-header';
import { LandingHero } from '@/components/landing/landing-hero';
import { ProcessStory } from '@/components/landing/process-story';
import { OutputSection } from '@/components/landing/output-section';
import { LANDING_COPY } from '@/components/landing/landing-copy';

/**
 * Hero использует утверждённый визуал из референса; пошаговое интерактивное
 * объяснение остаётся в отдельной секции ниже.
 */
export default function LandingPage() {
  return (
    <div className="landing-root font-sans min-h-screen bg-[#f3f6f8] text-[#171a1d]">
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
        <section id="capabilities" className="border-y border-[#d7dde2] bg-white">
          <div className="mx-auto max-w-[1280px] px-6 py-5 flex items-center justify-between text-xs font-mono tracking-wider text-[#66707a] uppercase">
            <span>вход: один эскиз или PDF</span>
            <span>.jpg · .png · .pdf</span>
          </div>
        </section>

        {/* SCROLL STORY — пять этапов */}
        <section id="how" className="mx-auto max-w-[1280px] px-6 pb-28 pt-24">
          <ProcessStory />
        </section>

        {/* РЕЗУЛЬТАТ */}
        <section className="border-t border-[#d7dde2] bg-white py-20">
          <div className="mx-auto max-w-[1280px] px-6">
            <OutputSection />
          </div>
        </section>
      </main>

      <footer className="border-t border-[#d7dde2] bg-white py-12">
        <div className="mx-auto max-w-[1280px] px-6 flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-[#66707a]">
          <span>{LANDING_COPY.footerCopyright}</span>
          <div className="flex gap-6">
            <a href="#main" className="hover:text-[#171a1d]">Наверх</a>
            <a href="#how" className="hover:text-[#171a1d]">Как работает</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
