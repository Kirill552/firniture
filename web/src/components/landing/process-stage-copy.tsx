'use client';

import React from 'react';
import { STAGES, type StageId, LANDING_COPY } from './landing-copy';

interface ProcessStageCopyProps {
  activeStage: StageId;
}

/**
 * Левая колонка истории при прокрутке.
 * Все пять этапов всегда в DOM (SSR / без JS / скринридеры).
 * Активный этап выделяется красной чертой, номером и жирным заголовком.
 * Текст — единственный источник смысла (чертёж скрыт через aria-hidden).
 */
export function ProcessStageCopy({ activeStage }: ProcessStageCopyProps) {
  return (
    <div>
      <div className="mb-3 font-tech text-[12px] uppercase tracking-[2px] text-[#8c8373]">
        Ход работы · 05 операций
      </div>
      <h2 className="font-display mb-10 max-w-[13ch] text-[40px] font-extrabold leading-[0.95] tracking-[-1.5px] text-[#17130d] md:text-[46px]">
        Как эскиз становится заказом
      </h2>

      <ol className="relative border-l-2 border-[#cec4ae]">
        {STAGES.map((stage) => {
          const isActive = stage.id === activeStage;
          return (
            <li
              key={stage.id}
              id={`stage-${stage.id}`}
              className="relative scroll-mt-24 py-5 pl-8 transition-all duration-300"
              style={{
                borderLeft: isActive ? '2px solid #d8352a' : '2px solid transparent',
                marginLeft: -2,
              }}
              aria-current={isActive ? 'step' : undefined}
            >
              {/* Узел */}
              <span
                className="font-tech absolute -left-[15px] top-6 flex h-7 w-7 items-center justify-center border-2 text-[12px] transition-colors duration-300"
                style={{
                  borderColor: isActive ? '#d8352a' : '#b3a88f',
                  background: isActive ? '#d8352a' : '#fbf8f1',
                  color: isActive ? '#fff' : '#8c8373',
                }}
              >
                {stage.id}
              </span>

              <h3
                className="mb-1 text-[18px] font-semibold tracking-[-0.2px] transition-colors duration-300"
                style={{ color: isActive ? '#17130d' : '#544c3f' }}
              >
                {stage.title}
              </h3>
              <p
                className="max-w-[40ch] text-[15px] leading-snug transition-colors duration-300"
                style={{ color: isActive ? '#544c3f' : '#8c8373' }}
              >
                {stage.description}
              </p>

              {stage.id === 5 && (
                <div className="mt-2 inline-flex items-center gap-2 border border-[#d8352a] px-2 py-1 text-[12px] font-medium text-[#d8352a]">
                  <span className="h-1.5 w-1.5 bg-[#d8352a]" />
                  После входа и вашего подтверждения
                </div>
              )}
            </li>
          );
        })}
      </ol>

      <p className="mt-8 max-w-[42ch] border-t border-[#cec4ae] pt-4 text-[13px] leading-relaxed text-[#8c8373]">
        {LANDING_COPY.ctaHint}
      </p>
    </div>
  );
}
