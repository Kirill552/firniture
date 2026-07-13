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
        <div className="mb-3 font-tech text-[12px] uppercase tracking-[2px] text-[#8c8373]">
          На выходе
        </div>
        <h3 className="font-display max-w-[16ch] text-[30px] font-bold leading-[1.05] tracking-[-1px] text-[#17130d]">
          {resultTitle}
        </h3>
        <p className="mt-5 max-w-[42ch] text-[15px] leading-relaxed text-[#544c3f]">
          {resultDescription}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:col-span-7">
        {cards.map((c) => (
          <div
            key={c.code}
            className="group flex flex-col justify-between border-2 border-[#17130d] bg-[#fbf8f1] p-6 transition-all hover:-translate-y-1 hover:shadow-[7px_7px_0_#17130d]"
          >
            <div>
              <div className="flex items-baseline justify-between">
                <span className="font-display text-[34px] font-extrabold tracking-[-1px] text-[#17130d]">
                  {c.code}
                </span>
                <span className="font-tech text-[11px] uppercase tracking-[1px] text-[#8c8373]">
                  формат
                </span>
              </div>
              <div className="mt-4 text-[15px] font-semibold text-[#17130d]">{c.title}</div>
              <div className="mt-1 text-[13px] text-[#8c8373]">{c.note}</div>
            </div>
            <div className="mt-6 flex items-center gap-2 border-t border-[#cec4ae] pt-3 text-[12px] font-medium text-[#d8352a]">
              <span className="h-1.5 w-1.5 bg-[#d8352a]" />
              После входа и подтверждения
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
