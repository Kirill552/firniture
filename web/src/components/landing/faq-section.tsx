import React from 'react';
import { FAQ_ITEMS } from './landing-copy';

/**
 * FAQ лендинга на <details>/<summary>: работает без JS (требование E2E),
 * индексируется краулерами, размечается FAQPage JSON-LD на уровне страницы.
 */
export function FaqSection() {
  return (
    <div className="grid grid-cols-1 gap-x-16 gap-y-10 lg:grid-cols-12">
      <div className="lg:col-span-4">
        <div className="mb-3 font-mono text-[10px] uppercase tracking-[2px] text-[#66707a]">
          Вопросы и ответы
        </div>
        <h2 className="mb-5 max-w-[16ch] text-[28px] md:text-[32px] font-extrabold leading-[0.98] tracking-[-1px] text-[#171a1d]">
          Что спрашивают перед первым эскизом
        </h2>
        <p className="max-w-[38ch] text-[15px] leading-relaxed text-[#66707a]">
          Коротко о форматах, бесплатном доступе и защите ваших заказов.
        </p>
      </div>

      <div className="lg:col-span-8">
        {FAQ_ITEMS.map((item) => (
          <details
            key={item.question}
            className="group border-b border-[#d7dde2] py-5 first:pt-0 last:border-b-0"
          >
            <summary className="flex cursor-pointer list-none items-baseline justify-between gap-4 text-[16px] font-bold text-[#171a1d] transition-colors hover:text-black [&::-webkit-details-marker]:hidden">
              <span>{item.question}</span>
              <span
                aria-hidden
                className="shrink-0 font-mono text-[14px] text-[#66707a] transition-transform duration-200 group-open:rotate-45"
              >
                +
              </span>
            </summary>
            <p className="mt-3 max-w-[62ch] text-[14px] leading-relaxed text-[#66707a]">
              {item.answer}
            </p>
          </details>
        ))}
      </div>
    </div>
  );
}
