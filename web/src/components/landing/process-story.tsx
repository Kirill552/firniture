'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useReducedMotion } from 'framer-motion';
import { STAGES, type StageId } from './landing-copy';
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

    const stageElements = Array.from(el.querySelectorAll<HTMLElement>('li[id^="stage-"]'));
    if (stageElements.length !== STAGES.length) return 0;

    const windowH = window.innerHeight || 800;
    const controlY = windowH * 0.35;
    let activeIndex = 0;

    for (let index = 1; index < stageElements.length; index += 1) {
      if (stageElements[index].getBoundingClientRect().top <= controlY) activeIndex = index;
    }

    const currentTop = stageElements[activeIndex].getBoundingClientRect().top;
    const nextTop = stageElements[activeIndex + 1]?.getBoundingClientRect().top;
    const span = nextTop === undefined ? windowH * 0.5 : nextTop - currentTop;
    const local = Math.max(0, Math.min(1, (controlY - currentTop) / Math.max(1, span)));

    return Math.min(1, (activeIndex + local) / STAGES.length);
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
    <div ref={storyRef} className={className} data-testid="process-story" data-active-stage={activeStage}>
      <div className="grid grid-cols-1 items-start gap-x-16 gap-y-12 lg:grid-cols-12">
        {/* Левая колонка — текст этапов и финальная зона удержания */}
        <div className="lg:col-span-5 lg:pb-[32vh]">
          <ProcessStageCopy activeStage={activeStage} />
        </div>

        {/* Правая колонка — липкий чертёжный лист (декоративный) */}
        <div className="lg:sticky lg:top-24 lg:col-span-7">
          <div className="relative">
            {/* Гигантский номер этапа за листом */}
            <div
              aria-hidden
              className="font-display pointer-events-none absolute -left-3 -top-16 select-none text-[150px] font-extrabold leading-none tracking-tighter text-[var(--brand-ink)]/[0.05]"
            >
              0{activeStage}
            </div>

            <div
              data-scene-mode="svg"
              className="relative bg-white border border-[#d7dde2] shadow-sm rounded-xl p-2.5"
            >
              <DraftingSheet stage={activeStage} progress={sheetProgress} />
            </div>

            {/* Индикатор этапов */}
            <div className="mt-5 flex items-center gap-3">
              <div className="flex gap-1.5">
                {([1, 2, 3, 4, 5] as StageId[]).map((s) => (
                  <span
                    key={s}
                    className="h-1.5 transition-all duration-300 rounded-full"
                    style={{
                      width: s === activeStage ? 28 : 12,
                      background: s === activeStage ? '#c7ff00' : '#d7dde2',
                    }}
                  />
                ))}
              </div>
              <span className="font-mono text-[10px] uppercase tracking-[1.5px] text-[#66707a]">
                прокрутите — чертёж пройдёт все этапы
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
