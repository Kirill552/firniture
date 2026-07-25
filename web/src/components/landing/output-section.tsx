'use client';

import React from 'react';
import { LANDING_COPY } from './landing-copy';

/**
 * Честный блок результата. DXF и PDF — после входа и подтверждения пользователем.
 * Заголовок и описание проверяются тестами копирайта.
 */
export function OutputSection() {
  const { resultTitle, resultDescription } = LANDING_COPY;

  const cards = [
    {
      code: 'DXF',
      title: 'Файл раскроя панелей',
      note: 'Контур, кромка, присадка по слоям',
    },
    {
      code: 'PDF',
      title: 'Спецификация и карта раскроя',
      note: 'Ведомость деталей и раскладка на листе',
    },
  ];

  return (
    <section className="grid grid-cols-1 gap-x-16 gap-y-10 lg:grid-cols-12">
      <div className="lg:col-span-5">
        <div className="mb-3 font-mono text-[10px] uppercase tracking-[2px] text-[#66707a]">
          На выходе
        </div>
        <h3 className="mb-5 max-w-[16ch] text-[28px] md:text-[32px] font-extrabold leading-[0.98] tracking-[-1px] text-[#171a1d]">
          {resultTitle}
        </h3>
        <p className="max-w-[42ch] text-[15px] leading-relaxed text-[#66707a]">
          {resultDescription}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:col-span-7">
        {cards.map((c) => (
          <div
            key={c.code}
            className="group flex flex-col justify-between border border-[#d7dde2] bg-white p-6 rounded-xl shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
          >
            <div>
              <div className="flex items-baseline justify-between">
                <span className="text-[34px] font-extrabold tracking-[-1px] text-[#171a1d]">
                  {c.code}
                </span>
                <span className="font-mono text-[10px] uppercase tracking-[1px] text-[#66707a]">
                  формат
                </span>
              </div>
              <div className="mt-4 text-[15px] font-bold text-[#171a1d]">{c.title}</div>
              <div className="mt-1 text-[13px] text-[#66707a]">{c.note}</div>
            </div>
            <div className="mt-6 flex items-center gap-1.5 border-t border-[#d7dde2] pt-3 text-[11px] font-semibold text-[#171a1d]">
              <span className="h-1.5 w-1.5 rounded-full bg-[#171a1d]" />
              После входа и подтверждения
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
