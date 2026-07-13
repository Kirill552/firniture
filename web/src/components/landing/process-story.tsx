'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useReducedMotion } from 'framer-motion';
import type { StageId } from './landing-copy';
import { ProcessStageCopy } from './process-stage-copy';
import { DraftingSheet } from './drafting-sheet';
import { resolveStageProgress } from './stage-progress';

interface ProcessStoryProps {
  className?: string;
}

/**
 * Координатор истории при прокрутке.
 * Прогресс секции [0..1] → activeStage + localProgress (см. resolveStageProgress).
 * Диапазоны: [0,0.2)→1 … [0.8,1]→5. Быстрая прокрутка, resize и reload
 * сразу дают корректный этап. Смысл всегда в HTML (SSR/no-js/скринридеры),
 * чертёж декоративен (aria-hidden). Только SVG — без WebGL и лишних чанков.
 */
export function ProcessStory({ className }: ProcessStoryProps) {
  const [activeStage, setActiveStage] = useState<StageId>(1);
  const [localProgress, setLocalProgress] = useState(0);
  const reduceMotion = useReducedMotion();

  const storyRef = useRef<HTMLDivElement>(null);

  const updateFromProgress = useCallback((progress: number) => {
    const { stage, localProgress: local } = resolveStageProgress(progress);
    setActiveStage(stage);
    setLocalProgress(Math.max(0, Math.min(1, local)));
  }, []);

  const calculateProgress = useCallback((): number => {
    const el = storyRef.current;
    if (!el) return 0;
    const rect = el.getBoundingClientRect();
    const windowH = window.innerHeight || 800;
    const start = rect.top - windowH * 0.3;
    const end = rect.bottom - windowH * 0.75;
    const total = Math.max(1, end - start);
    const current = -start;
    return Math.max(0, Math.min(1, current / total));
  }, []);

  const handleScroll = useCallback(() => {
    updateFromProgress(calculateProgress());
  }, [calculateProgress, updateFromProgress]);

  useEffect(() => {
    const onScroll = () => handleScroll();
    const onResize = () => updateFromProgress(calculateProgress());
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onResize);
    window.addEventListener('orientationchange', onResize);
    const raf = requestAnimationFrame(() => updateFromProgress(calculateProgress()));
    return () => {
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onResize);
      window.removeEventListener('orientationchange', onResize);
      cancelAnimationFrame(raf);
    };
  }, [calculateProgress, updateFromProgress, handleScroll]);

  useEffect(() => {
    const t = setTimeout(() => updateFromProgress(calculateProgress()), 60);
    return () => clearTimeout(t);
  }, [calculateProgress, updateFromProgress]);

  // При reduced-motion чертёж не «дорисовывается», а показан целиком.
  const sheetProgress = reduceMotion ? 1 : localProgress;

  return (
    <div ref={storyRef} className={className}>
      <div className="grid grid-cols-1 items-start gap-x-16 gap-y-12 lg:grid-cols-12">
        {/* Левая колонка — текст этапов (всегда в DOM) */}
        <div className="lg:col-span-5">
          <ProcessStageCopy activeStage={activeStage} />
        </div>

        {/* Правая колонка — липкий чертёжный лист (декоративный) */}
        <div className="lg:sticky lg:top-24 lg:col-span-7">
          <div className="relative">
            {/* Гигантский номер этапа за листом */}
            <div
              aria-hidden
              className="font-display pointer-events-none absolute -left-3 -top-16 select-none text-[150px] font-extrabold leading-none tracking-tighter text-[#17130d]/[0.06]"
            >
              0{activeStage}
            </div>

            <div
              data-scene-mode="svg"
              className="hardline hardshadow relative bg-[#fbf8f1] p-2"
            >
              <DraftingSheet stage={activeStage} progress={sheetProgress} />
            </div>

            {/* Индикатор этапов */}
            <div className="mt-5 flex items-center gap-3">
              <div className="flex gap-1.5">
                {([1, 2, 3, 4, 5] as StageId[]).map((s) => (
                  <span
                    key={s}
                    className="h-1.5 transition-all duration-300"
                    style={{
                      width: s === activeStage ? 28 : 12,
                      background: s === activeStage ? '#d8352a' : '#cec4ae',
                    }}
                  />
                ))}
              </div>
              <span className="font-tech text-[11px] uppercase tracking-[1.5px] text-[#8c8373]">
                прокрутите — чертёж пройдёт все этапы
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
