import { LandingHeader } from '@/components/landing/landing-header';
import { LandingHero } from '@/components/landing/landing-hero';
import { ProcessStory } from '@/components/landing/process-story';
import { OutputSection } from '@/components/landing/output-section';
import { FaqSection } from '@/components/landing/faq-section';
import { FinalCtaSection } from '@/components/landing/final-cta-section';
import { LandingFooter } from '@/components/landing/landing-footer';
import { FAQ_ITEMS } from '@/components/landing/landing-copy';
import { LEGAL } from '@/lib/legal';

/**
 * Hero использует утверждённый визуал из референса; пошаговое интерактивное
 * объяснение остаётся в отдельной секции ниже.
 */
export default function LandingPage() {
  // schema.org FAQPage: расширенный сниппет в Яндексе и Google
  const faqJsonLd = {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: FAQ_ITEMS.map((item) => ({
      '@type': 'Question',
      name: item.question,
      acceptedAnswer: {
        '@type': 'Answer',
        text: item.answer,
      },
    })),
  };

  const orgJsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: LEGAL.serviceName,
    url: LEGAL.siteUrl,
    email: LEGAL.email,
  };

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
        <section id="result" className="border-t border-[#d7dde2] bg-white py-20">
          <div className="mx-auto max-w-[1280px] px-6">
            <OutputSection />
          </div>
        </section>

        {/* FAQ */}
        <section id="faq" className="border-t border-[#d7dde2] py-20">
          <div className="mx-auto max-w-[1280px] px-6">
            <FaqSection />
          </div>
        </section>

        {/* Финальный CTA */}
        <section className="border-t border-[#d7dde2] bg-white py-20">
          <div className="mx-auto max-w-[1280px] px-6">
            <FinalCtaSection />
          </div>
        </section>
      </main>

      <footer className="border-t border-[#d7dde2] bg-white">
        <LandingFooter />
      </footer>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(orgJsonLd) }}
      />
    </div>
  );
}
