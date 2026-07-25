import Image from 'next/image';
import Link from 'next/link';

import { LANDING_COPY } from './landing-copy';

export function LandingHero() {
  const { heroOverline, h1, heroDescription, ctaPrimary, ctaHint } = LANDING_COPY;

  return (
    <div className="grid grid-cols-1 items-center gap-x-8 gap-y-10 pb-16 pt-14 lg:grid-cols-12 lg:pb-20 lg:pt-16">
      {/* Левая колонка */}
      <div className="lg:col-span-5">
        <div
          data-rise
          style={{ animationDelay: '0.05s' }}
          className="mb-6 inline-flex items-center gap-2 border border-[#d7dde2] bg-white px-3 py-1.5 rounded-full text-xs font-semibold text-[#171a1d]"
        >
          <span className="h-2 w-2 rounded-full bg-[#c7ff00]" />
          <span className="text-[11px] uppercase tracking-[1.5px] text-[#66707a]">
            {heroOverline}
          </span>
        </div>

        <h1
          data-rise
          style={{ animationDelay: '0.14s' }}
          className="mb-7 max-w-[15ch] text-[46px] font-extrabold leading-[0.98] tracking-[-2px] text-[#171a1d] sm:text-[58px] xl:text-[68px]"
        >
          {h1}
        </h1>

        <p
          data-rise
          style={{ animationDelay: '0.24s' }}
          className="mb-9 max-w-[46ch] text-[16px] md:text-[18px] leading-[1.55] text-[#66707a]"
        >
          {heroDescription}
        </p>

        <div data-rise style={{ animationDelay: '0.34s' }}>
          <Link
            href="/new"
            className="group inline-flex h-14 w-fit items-center gap-3 bg-[#c7ff00] hover:bg-[#aee600] text-[#171a1d] px-8 text-[17px] font-bold rounded-xl active:scale-[0.98] transition-all duration-150 cursor-pointer shadow-sm"
          >
            {ctaPrimary}
            <span className="transition-transform group-hover:translate-x-1">→</span>
          </Link>
          <p className="mt-4 flex max-w-[52ch] items-start gap-2.5 text-[12px] leading-relaxed text-[#66707a]">
            <span className="mt-2 h-px w-6 shrink-0 bg-[#d7dde2]" />
            {ctaHint}
          </p>
        </div>
      </div>

      {/* Утверждённый визуал: эскиз → детали → собранная кухня */}
      <div data-rise style={{ animationDelay: '0.3s' }} className="lg:col-span-7">
        <Image
          src="/hero-kitchen-seamless.webp"
          width={919}
          height={800}
          priority
          sizes="(min-width: 1024px) 58vw, 100vw"
          alt="Эскиз, детали и собранная кухня"
          className="h-auto w-full select-none object-contain [mask-image:linear-gradient(to_right,transparent_0%,black_4%,black_100%)]"
        />
      </div>
    </div>
  );
}
