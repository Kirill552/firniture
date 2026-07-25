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
      <div className="mb-3 font-mono text-[10px] uppercase tracking-[2px] text-[#66707a]">
        Ход работы · 05 операций
      </div>
      <h2 className="mb-10 max-w-[13ch] text-[36px] md:text-[40px] font-extrabold leading-[0.98] tracking-[-1.5px] text-[#171a1d]">
        Как эскиз становится заказом
      </h2>

      <ol className="relative border-l-2 border-[#d7dde2]">
        {STAGES.map((stage) => {
          const isActive = stage.id === activeStage;
          return (
            <li
              key={stage.id}
              id={`stage-${stage.id}`}
              className="relative scroll-mt-24 py-5 pl-8 transition-all duration-300"
              style={{
                borderLeft: isActive ? '2px solid #171a1d' : '2px solid transparent',
                marginLeft: -2,
              }}
              aria-current={isActive ? 'step' : undefined}
            >
              {/* Узел */}
              <span
                className="font-mono absolute -left-[15px] top-6 flex h-7 w-7 items-center justify-center border-2 text-[12px] transition-colors duration-300 rounded-full"
                style={{
                  borderColor: isActive ? '#171a1d' : '#d7dde2',
                  background: isActive ? '#c7ff00' : '#ffffff',
                  color: isActive ? '#171a1d' : '#66707a',
                }}
              >
                {stage.id}
              </span>

              <h3
                className="mb-1 text-[18px] font-bold tracking-[-0.2px] transition-colors duration-300"
                style={{ color: isActive ? '#171a1d' : '#66707a' }}
              >
                {stage.title}
              </h3>
              <p
                className="max-w-[40ch] text-[14px] leading-relaxed transition-colors duration-300"
                style={{ color: isActive ? '#171a1d' : '#66707a' }}
              >
                {stage.description}
              </p>

              {stage.id === 5 && (
                <div className="mt-2 inline-flex items-center gap-1.5 border border-[#d7dde2] bg-[#c7ff00]/10 px-2.5 py-1 text-[11px] font-medium text-[#171a1d] rounded-lg">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#171a1d]" />
                  После входа и вашего подтверждения
                </div>
              )}
            </li>
          );
        })}
      </ol>

      <p className="mt-8 max-w-[42ch] border-t border-[#d7dde2] pt-4 text-[12px] leading-relaxed text-[#66707a]">
        {LANDING_COPY.ctaHint}
      </p>
    </div>
  );
}
