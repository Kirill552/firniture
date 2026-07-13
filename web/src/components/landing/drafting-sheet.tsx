'use client';

import React from 'react';
import type { StageId } from './landing-copy';
import { NestingLayout } from './nesting-layout';

/**
 * «Чертёжная доска» — главный визуальный приём лендинга.
 * Один и тот же чертёж корпуса кухонного шкафа проходит пять этапов:
 * набросок → размеры → уточнение → состав → раскрой.
 * Ничего не «разлетается»: элевация остаётся якорем, меняются только слои
 * аннотаций. Управляется stage + progress (прокрутка). Чистая SVG, без WebGL.
 * Декоративна: весь смысл продублирован текстом, поэтому aria-hidden.
 */

const C = {
  ink: '#17130d',
  graphite: '#544c3f',
  muted: '#8c8373',
  line: '#cec4ae',
  lineStrong: '#b3a88f',
  red: '#d8352a',
  sheet: '#fbf8f1',
  door: '#efe7d6',
  hatch: '#e7dec9',
};

// Геометрия элевации корпуса
const BODY = { x: 96, y: 104, w: 252, h: 284 };
const X1 = BODY.x + BODY.w; // 348
const Y1 = BODY.y + BODY.h; // 388
const T = 15; // толщина плиты
const REVEAL = 220; // центр раствора фасадов

function clamp(v: number): number {
  return Math.max(0, Math.min(1, v));
}

interface DraftingSheetProps {
  stage: StageId;
  progress: number;
  hero?: boolean;
}

export function DraftingSheet({ stage, progress, hero = false }: DraftingSheetProps) {
  const eff: StageId = hero ? 2 : stage;
  const drawn = hero ? 1 : clamp(progress);

  const show = (s: StageId) => (eff === s ? 1 : 0);
  const dimsOn = eff >= 2 && eff <= 4 ? 1 : 0;
  const cabinetOn = eff <= 4 ? 1 : 0;
  const dimDraw = eff === 2 ? clamp(drawn * 1.25) : eff > 2 ? 1 : 0;

  return (
    <svg
      viewBox="0 0 680 480"
      role="img"
      aria-hidden="true"
      className="cad-cursor"
      style={{ width: '100%', height: 'auto', display: 'block', background: C.sheet }}
    >
      <defs>
        <marker id="ar-a" markerWidth="9" markerHeight="9" refX="5" refY="4.5" orient="auto">
          <path d="M1,1 L7,4.5 L1,8" fill="none" stroke={C.red} strokeWidth="1.2" />
        </marker>
        <pattern id="ar-hatch" width="7" height="7" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
          <line x1="0" y1="0" x2="0" y2="7" stroke={C.lineStrong} strokeWidth="0.7" />
        </pattern>
      </defs>

      {/* Рамка листа + внутренняя рамка чертежа */}
      <rect x="8" y="8" width="664" height="464" fill={C.sheet} stroke={C.ink} strokeWidth="2.5" />
      <rect x="22" y="22" width="636" height="436" fill="none" stroke={C.line} strokeWidth="1" />
      {[[22, 22], [658, 22], [22, 458], [658, 458]].map(([cx, cy], i) => (
        <g key={i} stroke={C.lineStrong} strokeWidth="1">
          <line x1={cx - 7} y1={cy} x2={cx + 7} y2={cy} />
          <line x1={cx} y1={cy - 7} x2={cx} y2={cy + 7} />
        </g>
      ))}

      {/* Штамп-заголовок этапа (верхний левый угол) */}
      <text x="36" y="46" fontSize="12" fontFamily="var(--font-tech), monospace" fill={C.muted} letterSpacing="1.5">
        ЭТАП 0{eff} / 05
      </text>
      <line x1="36" y1="54" x2="150" y2="54" stroke={C.red} strokeWidth="2" />

      {/* ==================== СТАДИЯ 1 — набросок ==================== */}
      <g style={{ opacity: show(1), transition: 'opacity 0.45s ease' }}>
        <path
          d={`M${BODY.x + 2},${BODY.y + 3} C ${BODY.x + 90},${BODY.y - 3} ${X1 - 80},${BODY.y + 6} ${X1 - 1},${BODY.y + 1}
              C ${X1 + 4},${BODY.y + 120} ${X1 - 2},${Y1 - 90} ${X1 + 1},${Y1 - 1}
              C ${X1 - 90},${Y1 + 5} ${BODY.x + 80},${Y1 - 4} ${BODY.x + 1},${Y1 + 2}
              C ${BODY.x - 4},${Y1 - 120} ${BODY.x + 3},${BODY.y + 100} ${BODY.x + 2},${BODY.y + 3} Z`}
          fill="none"
          stroke={C.graphite}
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path
          d={`M${BODY.x + 10},250 C 160,246 250,254 ${X1 - 8},249`}
          fill="none"
          stroke={C.graphite}
          strokeWidth="1.6"
          strokeLinecap="round"
          opacity="0.7"
        />
        <path
          d={`M${REVEAL},${BODY.y + 20} C ${REVEAL - 3},200 ${REVEAL + 4},300 ${REVEAL},${Y1 - 18}`}
          fill="none"
          stroke={C.graphite}
          strokeWidth="1.6"
          strokeLinecap="round"
          opacity="0.7"
        />
        <FileTag x={250} y={132} />
        <text x={BODY.x} y={Y1 + 34} fontSize="13" fontFamily="var(--font-tech), monospace" fill={C.graphite}>
          от руки: ≈ 600 × 720 ?
        </text>
      </g>

      {/* ==================== Корпус (элевация) для этапов 2–4 ==================== */}
      <g style={{ opacity: cabinetOn && eff !== 1 ? 1 : 0, transition: 'opacity 0.45s ease' }}>
        {/* Штриховка плит (состав, этап 4) */}
        <g style={{ opacity: show(4), transition: 'opacity 0.4s ease' }}>
          <rect x={BODY.x} y={BODY.y} width={T} height={BODY.h} fill="url(#ar-hatch)" />
          <rect x={X1 - T} y={BODY.y} width={T} height={BODY.h} fill="url(#ar-hatch)" />
          <rect x={BODY.x} y={BODY.y} width={BODY.w} height={T} fill="url(#ar-hatch)" />
          <rect x={BODY.x} y={Y1 - T} width={BODY.w} height={T} fill="url(#ar-hatch)" />
          <rect x={BODY.x + T} y={244} width={BODY.w - 2 * T} height={10} fill="url(#ar-hatch)" />
        </g>

        {/* Корпус */}
        <rect x={BODY.x} y={BODY.y} width={BODY.w} height={BODY.h} fill="none" stroke={C.ink} strokeWidth="2.4" />
        <rect x={BODY.x + T} y={BODY.y + T} width={BODY.w - 2 * T} height={BODY.h - 2 * T} fill="none" stroke={C.ink} strokeWidth="1.2" />
        {/* Полка */}
        <rect x={BODY.x + T} y={244} width={BODY.w - 2 * T} height={10} fill={C.door} stroke={C.ink} strokeWidth="1.2" />
        {/* Фасады (двери) */}
        <rect x={BODY.x + T + 4} y={BODY.y + T + 4} width={REVEAL - (BODY.x + T + 4) - 4} height={BODY.h - 2 * T - 8} fill={C.door} stroke={C.ink} strokeWidth="1.1" />
        <rect x={REVEAL + 4} y={BODY.y + T + 4} width={X1 - T - 4 - (REVEAL + 4)} height={BODY.h - 2 * T - 8} fill={C.door} stroke={C.ink} strokeWidth="1.1" />
        {/* Ручки */}
        <line x1={REVEAL - 10} y1={230} x2={REVEAL - 10} y2={262} stroke={C.ink} strokeWidth="2.4" strokeLinecap="round" />
        <line x1={REVEAL + 10} y1={230} x2={REVEAL + 10} y2={262} stroke={C.ink} strokeWidth="2.4" strokeLinecap="round" />
      </g>

      {/* ==================== Размерные линии (этапы 2–4) ==================== */}
      <g style={{ opacity: dimsOn, transition: 'opacity 0.4s ease' }}>
        {/* Ширина сверху */}
        <line x1={BODY.x} y1={BODY.y} x2={BODY.x} y2={78} stroke={C.lineStrong} strokeWidth="0.8" />
        <line x1={X1} y1={BODY.y} x2={X1} y2={78} stroke={C.lineStrong} strokeWidth="0.8" />
        <line
          x1={BODY.x} y1={86} x2={X1} y2={86}
          stroke={C.red} strokeWidth="1.3" markerStart="url(#ar-a)" markerEnd="url(#ar-a)"
          pathLength={1} strokeDasharray={1} strokeDashoffset={1 - dimDraw}
        />
        <rect x={200} y={78} width={44} height={17} fill={C.sheet} />
        <text x={222} y={91} fontSize="13" fontFamily="var(--font-tech), monospace" fill={C.ink} textAnchor="middle">600</text>

        {/* Высота слева */}
        <line x1={BODY.x} y1={BODY.y} x2={70} y2={BODY.y} stroke={C.lineStrong} strokeWidth="0.8" />
        <line x1={BODY.x} y1={Y1} x2={70} y2={Y1} stroke={C.lineStrong} strokeWidth="0.8" />
        <line
          x1={62} y1={BODY.y} x2={62} y2={Y1}
          stroke={C.red} strokeWidth="1.3" markerStart="url(#ar-a)" markerEnd="url(#ar-a)"
          pathLength={1} strokeDasharray={1} strokeDashoffset={1 - dimDraw}
        />
        <g transform="translate(52 246)">
          <rect x={-9} y={-22} width={17} height={44} fill={C.sheet} />
          <text x={0} y={4} fontSize="13" fontFamily="var(--font-tech), monospace" fill={C.ink} textAnchor="middle" transform="rotate(-90)">720</text>
        </g>

        {/* Глубина — изометрическая выноска */}
        <line x1={X1} y1={BODY.y} x2={X1 + 34} y2={BODY.y - 22} stroke={C.lineStrong} strokeWidth="0.8" />
        <text x={X1 + 40} y={BODY.y - 20} fontSize="11" fontFamily="var(--font-tech), monospace" fill={C.graphite}>560 гл.</text>

        {/* Материал */}
        <g style={{ opacity: eff >= 2 ? 1 : 0 }}>
          <rect x={128} y={300} width={78} height={20} fill={C.sheet} stroke={C.ink} strokeWidth="1" />
          <text x={135} y={314} fontSize="11" fontFamily="var(--font-tech), monospace" fill={C.ink}>ЛДСП 16</text>
        </g>
      </g>

      {/* ==================== СТАДИЯ 3 — уточнение ==================== */}
      <g style={{ opacity: show(3), transition: 'opacity 0.4s ease' }}>
        <rect
          x={REVEAL + 2} y={BODY.y + T + 2} width={X1 - T - 2 - (REVEAL + 2)} height={BODY.h - 2 * T - 4}
          fill="none" stroke={C.red} strokeWidth="2.4" strokeDasharray="7 4"
        />
        <g data-blink>
          <circle cx={X1 - 6} cy={BODY.y + 8} r={13} fill={C.red} />
          <text x={X1 - 6} y={BODY.y + 13} fontSize="16" fontFamily="var(--font-display), sans-serif" fontWeight="700" fill="#fff" textAnchor="middle">?</text>
        </g>
        <g transform={`translate(96 ${Y1 + 16})`}>
          <rect x={0} y={0} width={330} height={30} fill="#fff" stroke={C.red} strokeWidth="1.6" />
          <text x={12} y={20} fontSize="13" fontFamily="var(--font-golos), sans-serif" fontWeight="600" fill={C.ink}>
            Фасад накладной или вкладной?
          </text>
        </g>
      </g>

      {/* ==================== СТАДИЯ 4 — состав (ведомость) ==================== */}
      <g style={{ opacity: show(4), transition: 'opacity 0.4s ease' }}>
        <PartsLedger />
        {/* Выноски от деталей к ведомости */}
        <line x1={BODY.x + T / 2} y1={160} x2={392} y2={132} stroke={C.line} strokeWidth="0.8" />
        <line x1={BODY.x + BODY.w / 2} y1={249} x2={392} y2={196} stroke={C.line} strokeWidth="0.8" />
        <line x1={264} y1={300} x2={392} y2={224} stroke={C.line} strokeWidth="0.8" />
      </g>

      {/* ==================== СТАДИЯ 5 — раскрой ==================== */}
      <g style={{ opacity: show(5), transition: 'opacity 0.45s ease' }}>
        {eff === 5 && (
          <NestingLayout progress={drawn} ink={C.ink} sheet={C.sheet} line={C.line} red={C.red} muted={C.muted} />
        )}
        {/* Мини-превью корпуса */}
        <g transform="translate(70 96) scale(0.42)">
          <rect x={0} y={0} width={252} height={284} fill="none" stroke={C.graphite} strokeWidth="3" />
          <line x1={0} y1={148} x2={252} y2={148} stroke={C.graphite} strokeWidth="2" />
          <line x1={126} y1={0} x2={126} y2={284} stroke={C.graphite} strokeWidth="2" />
        </g>
        <StampBadge x={70} y={224} label="DXF" />
        <StampBadge x={150} y={224} label="PDF" />
        <text x={70} y={300} fontSize="11" fontFamily="var(--font-tech), monospace" fill={C.red}>
          после входа и подтверждения
        </text>
      </g>

      {/* ==================== Штамп (title block) ==================== */}
      <TitleBlock stage={eff} />
    </svg>
  );
}

/* ---------- Вспомогательные фигуры ---------- */

function FileTag({ x, y }: { x: number; y: number }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <path d="M0,0 H92 V26 H0 Z" fill="#fff" stroke={C.ink} strokeWidth="1.2" />
      <path d="M80,0 L92,0 L92,12 Z" fill={C.hatch} stroke={C.ink} strokeWidth="1" />
      <text x={9} y={17} fontSize="11" fontFamily="var(--font-tech), monospace" fill={C.graphite}>эскиз_кухни.jpg</text>
    </g>
  );
}

function StampBadge({ x, y, label }: { x: number; y: number; label: string }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <rect x={0} y={0} width={68} height={40} fill="#fff" stroke={C.ink} strokeWidth="2" />
      <text x={34} y={27} fontSize="17" fontFamily="var(--font-display), sans-serif" fontWeight="700" fill={C.ink} textAnchor="middle">{label}</text>
    </g>
  );
}

function PartsLedger() {
  const rows = ['2 × боковина', 'верх · дно', 'полка', '2 × фасад', 'кромка ПВХ 2 мм'];
  return (
    <g transform="translate(396 108)">
      <rect x={0} y={0} width={252} height={188} fill="#fff" stroke={C.ink} strokeWidth="1.6" />
      <rect x={0} y={0} width={252} height={26} fill={C.ink} />
      <text x={12} y={18} fontSize="12" fontFamily="var(--font-tech), monospace" fill="#fff" letterSpacing="1">ВЕДОМОСТЬ ДЕТАЛЕЙ</text>
      {rows.map((r, i) => (
        <g key={i} transform={`translate(0 ${34 + i * 26})`}>
          <text x={12} y={12} fontSize="12.5" fontFamily="var(--font-golos), sans-serif" fill={C.ink}>{r}</text>
          <line x1={0} y1={20} x2={252} y2={20} stroke={C.line} strokeWidth="0.8" />
        </g>
      ))}
      <text x={12} y={178} fontSize="12" fontFamily="var(--font-tech), monospace" fill={C.red}>7 деталей · 12 присадок</text>
    </g>
  );
}

function TitleBlock({ stage }: { stage: StageId }) {
  const captions: Record<StageId, string> = {
    1: 'приём эскиза',
    2: 'обмер',
    3: 'согласование',
    4: 'спецификация',
    5: 'раскрой',
  };
  return (
    <g transform="translate(452 402)">
      <defs>
        <clipPath id="title-order-clip">
          <rect x={2} y={27} width={43} height={21} />
        </clipPath>
        <clipPath id="title-stage-clip">
          <rect x={47} y={27} width={71} height={21} />
        </clipPath>
        <clipPath id="title-material-clip">
          <rect x={122} y={27} width={72} height={21} />
        </clipPath>
      </defs>
      <rect x={0} y={0} width={196} height={50} fill="#fff" stroke={C.ink} strokeWidth="2" />
      <line x1={0} y1={25} x2={196} y2={25} stroke={C.ink} strokeWidth="1" />
      <line x1={120} y1={0} x2={120} y2={50} stroke={C.ink} strokeWidth="1" />
      <line x1={46} y1={25} x2={46} y2={50} stroke={C.ink} strokeWidth="1" />
      <text x={9} y={16} fontSize="12" fontFamily="var(--font-display), sans-serif" fontWeight="700" fill={C.ink}>АвтоРаскрой</text>
      <text
        data-title-cell="order"
        x={7}
        y={41}
        fontSize="9"
        fontFamily="var(--font-tech), monospace"
        fill={C.graphite}
        clipPath="url(#title-order-clip)"
      >
        Б-600
      </text>
      <text
        data-title-cell="stage"
        x={51}
        y={41}
        fontSize="8.5"
        fontFamily="var(--font-tech), monospace"
        fill={C.graphite}
        clipPath="url(#title-stage-clip)"
      >
        {captions[stage]}
      </text>
      <text x={130} y={16} fontSize="10" fontFamily="var(--font-tech), monospace" fill={C.muted}>М 1:10</text>
      <text
        data-title-cell="material"
        x={130}
        y={41}
        fontSize="10"
        fontFamily="var(--font-tech), monospace"
        fill={C.muted}
        clipPath="url(#title-material-clip)"
      >
        ЛДСП 16
      </text>
    </g>
  );
}
