'use client';

import React from 'react';

/**
 * Этап 5 — карта раскроя (nesting). Детали шкафа разложены на листе ЛДСП,
 * как в реальном DXF. Появляются по очереди в зависимости от progress,
 * что читается как «сервис раскладывает панели на лист».
 * Чистая SVG-группа, вкладывается в общий чертёжный лист. aria-hidden сверху.
 */

interface Part {
  x: number;
  y: number;
  w: number;
  h: number;
  label: string;
}

// Аккуратная упаковка деталей корпуса на условном листе 2800×2070.
const PARTS: Part[] = [
  { x: 250, y: 96, w: 52, h: 188, label: 'боковина' },
  { x: 306, y: 96, w: 52, h: 188, label: 'боковина' },
  { x: 362, y: 96, w: 150, h: 40, label: 'верх' },
  { x: 362, y: 140, w: 150, h: 40, label: 'дно' },
  { x: 362, y: 184, w: 150, h: 34, label: 'полка' },
  { x: 362, y: 222, w: 72, h: 62, label: 'фасад' },
  { x: 438, y: 222, w: 74, h: 62, label: 'фасад' },
];

function partOpacity(progress: number, index: number): number {
  // Детали «выкладываются» одна за другой на протяжении прокрутки этапа.
  const t = (progress - index * 0.11) * 4;
  return Math.max(0, Math.min(1, t));
}

interface NestingLayoutProps {
  progress: number;
  ink: string;
  sheet: string;
  line: string;
  red: string;
  muted: string;
}

export function NestingLayout({ progress, ink, sheet, line, red, muted }: NestingLayoutProps) {
  return (
    <g>
      {/* Лист материала */}
      <rect x={240} y={82} width={286} height={214} fill={sheet} stroke={ink} strokeWidth={2} />
      <text x={248} y={76} fontSize={11} fontFamily="var(--font-tech), monospace" fill={muted}>
        ЛИСТ ЛДСП · 2800 × 2070
      </text>

      {/* Каретка-сканер: тонкая красная линия проходит по листу */}
      <g clipPath="url(#nest-clip)">
        <rect
          x={240}
          y={82}
          width={2}
          height={214}
          fill={red}
          opacity={progress > 0.02 && progress < 0.98 ? 0.7 : 0}
          style={{
            transform: `translateX(${Math.min(1, progress) * 284}px)`,
            transition: 'transform 0.12s linear',
          }}
        />
      </g>
      <defs>
        <clipPath id="nest-clip">
          <rect x={240} y={82} width={286} height={214} />
        </clipPath>
      </defs>

      {/* Детали */}
      {PARTS.map((p, i) => {
        const o = partOpacity(progress, i);
        return (
          <g key={i} style={{ opacity: o, transition: 'opacity 0.18s linear' }}>
            <rect
              x={p.x}
              y={p.y}
              width={p.w}
              height={p.h}
              fill="#efe7d6"
              stroke={ink}
              strokeWidth={1.3}
            />
            {/* Штриховка направления волокна */}
            <line
              x1={p.x + 4}
              y1={p.y + p.h - 4}
              x2={p.x + Math.min(p.w, p.h) - 4}
              y2={p.y + 4}
              stroke={line}
              strokeWidth={0.8}
            />
            <text
              x={p.x + p.w / 2}
              y={p.y + p.h / 2 + 3}
              fontSize={8.5}
              fontFamily="var(--font-tech), monospace"
              fill={ink}
              textAnchor="middle"
            >
              {p.label}
            </text>
          </g>
        );
      })}

      {/* Итог по раскрою */}
      <g style={{ opacity: partOpacity(progress, PARTS.length - 1), transition: 'opacity 0.2s linear' }}>
        <text x={248} y={312} fontSize={10} fontFamily="var(--font-tech), monospace" fill={ink}>
          7 деталей · полезный выход 94%
        </text>
      </g>
    </g>
  );
}
