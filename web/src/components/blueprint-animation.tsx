'use client'

import { motion, useAnimation } from 'framer-motion'
import { useEffect } from 'react'

/**
 * BlueprintAnimation - анимация трансформации эскиза в технический чертёж
 *
 * Фазы:
 * 1. Линии "рисуются" с эффектом stroke-dasharray
 * 2. Появляются размерные линии
 * 3. Появляются аннотации
 */
export function BlueprintAnimation() {
  const controls = useAnimation()

  useEffect(() => {
    const sequence = async () => {
      // Запускаем анимацию с задержкой для красивого эффекта
      await controls.start('visible')
    }
    sequence()
  }, [controls])

  // Варианты анимации для линий чертежа
  const pathVariants = {
    hidden: {
      pathLength: 0,
      opacity: 0,
    },
    visible: (i: number) => ({
      pathLength: 1,
      opacity: 1,
      transition: {
        pathLength: {
          delay: i * 0.15,
          duration: 1.2,
          ease: 'easeInOut' as const,
        },
        opacity: {
          delay: i * 0.15,
          duration: 0.3,
        },
      },
    }),
  }

  // Варианты для размерных линий (появляются позже)
  const dimensionVariants = {
    hidden: {
      pathLength: 0,
      opacity: 0,
    },
    visible: (i: number) => ({
      pathLength: 1,
      opacity: 0.6,
      transition: {
        pathLength: {
          delay: 2 + i * 0.1,
          duration: 0.6,
          ease: 'easeOut' as const,
        },
        opacity: {
          delay: 2 + i * 0.1,
          duration: 0.3,
        },
      },
    }),
  }

  // Варианты для текста размеров
  const textVariants = {
    hidden: {
      opacity: 0,
      y: 5,
    },
    visible: (i: number) => ({
      opacity: 0.5,
      y: 0,
      transition: {
        delay: 2.5 + i * 0.15,
        duration: 0.4,
        ease: 'easeOut' as const,
      },
    }),
  }

  // Варианты для точек/маркеров
  const dotVariants = {
    hidden: {
      scale: 0,
      opacity: 0,
    },
    visible: (i: number) => ({
      scale: 1,
      opacity: 0.4,
      transition: {
        delay: 1.8 + i * 0.08,
        duration: 0.3,
        type: 'spring' as const,
        stiffness: 300,
      },
    }),
  }

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      <svg
        viewBox="0 0 800 600"
        className="absolute w-full h-full opacity-[0.15] dark:opacity-[0.12]"
        style={{
          left: '50%',
          top: '50%',
          transform: 'translate(-50%, -50%) scale(1.2)',
          maxWidth: '1200px',
          maxHeight: '800px',
        }}
      >
        {/* Основной контур кухни - изометрический вид */}
        <g
          fill="none"
          className="stroke-foreground"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          {/* Нижние шкафы - фронтальная часть */}
          <motion.path
            d="M 150 400 L 150 280 L 650 280 L 650 400 L 150 400"
            variants={pathVariants}
            initial="hidden"
            animate={controls}
            custom={0}
          />

          {/* Разделители нижних шкафов */}
          <motion.path
            d="M 250 280 L 250 400"
            variants={pathVariants}
            initial="hidden"
            animate={controls}
            custom={1}
          />
          <motion.path
            d="M 400 280 L 400 400"
            variants={pathVariants}
            initial="hidden"
            animate={controls}
            custom={2}
          />
          <motion.path
            d="M 550 280 L 550 400"
            variants={pathVariants}
            initial="hidden"
            animate={controls}
            custom={3}
          />

          {/* Ручки нижних шкафов */}
          <motion.path
            d="M 190 340 L 220 340"
            variants={pathVariants}
            initial="hidden"
            animate={controls}
            custom={4}
            strokeWidth="2"
          />
          <motion.path
            d="M 290 340 L 360 340"
            variants={pathVariants}
            initial="hidden"
            animate={controls}
            custom={4.5}
            strokeWidth="2"
          />
          <motion.path
            d="M 440 340 L 510 340"
            variants={pathVariants}
            initial="hidden"
            animate={controls}
            custom={5}
            strokeWidth="2"
          />
          <motion.path
            d="M 590 340 L 620 340"
            variants={pathVariants}
            initial="hidden"
            animate={controls}
            custom={5.5}
            strokeWidth="2"
          />

          {/* Столешница */}
          <motion.path
            d="M 140 280 L 140 265 L 660 265 L 660 280"
            variants={pathVariants}
            initial="hidden"
            animate={controls}
            custom={6}
            strokeWidth="2"
          />

          {/* Верхние шкафы */}
          <motion.path
            d="M 150 120 L 150 220 L 450 220 L 450 120 L 150 120"
            variants={pathVariants}
            initial="hidden"
            animate={controls}
            custom={7}
          />

          {/* Разделители верхних шкафов */}
          <motion.path
            d="M 250 120 L 250 220"
            variants={pathVariants}
            initial="hidden"
            animate={controls}
            custom={8}
          />
          <motion.path
            d="M 350 120 L 350 220"
            variants={pathVariants}
            initial="hidden"
            animate={controls}
            custom={9}
          />

          {/* Ручки верхних шкафов */}
          <motion.path
            d="M 190 180 L 220 180"
            variants={pathVariants}
            initial="hidden"
            animate={controls}
            custom={10}
            strokeWidth="2"
          />
          <motion.path
            d="M 290 180 L 320 180"
            variants={pathVariants}
            initial="hidden"
            animate={controls}
            custom={10.5}
            strokeWidth="2"
          />
          <motion.path
            d="M 390 180 L 420 180"
            variants={pathVariants}
            initial="hidden"
            animate={controls}
            custom={11}
            strokeWidth="2"
          />

          {/* Вытяжка */}
          <motion.path
            d="M 500 120 L 500 200 L 620 200 L 620 120 L 500 120"
            variants={pathVariants}
            initial="hidden"
            animate={controls}
            custom={12}
          />
          <motion.path
            d="M 530 200 L 530 220 L 590 220 L 590 200"
            variants={pathVariants}
            initial="hidden"
            animate={controls}
            custom={13}
          />

          {/* Плита (варочная панель) */}
          <motion.circle
            cx="540"
            cy="272"
            r="12"
            variants={pathVariants}
            initial="hidden"
            animate={controls}
            custom={14}
          />
          <motion.circle
            cx="580"
            cy="272"
            r="12"
            variants={pathVariants}
            initial="hidden"
            animate={controls}
            custom={14.5}
          />
          <motion.circle
            cx="540"
            cy="258"
            r="8"
            variants={pathVariants}
            initial="hidden"
            animate={controls}
            custom={15}
          />
          <motion.circle
            cx="580"
            cy="258"
            r="8"
            variants={pathVariants}
            initial="hidden"
            animate={controls}
            custom={15.5}
          />

          {/* Мойка */}
          <motion.path
            d="M 170 265 L 170 255 Q 200 245 230 255 L 230 265"
            variants={pathVariants}
            initial="hidden"
            animate={controls}
            custom={16}
          />
          <motion.circle
            cx="200"
            cy="260"
            r="3"
            variants={pathVariants}
            initial="hidden"
            animate={controls}
            custom={16.5}
          />
        </g>

        {/* Размерные линии */}
        <g
          fill="none"
          className="stroke-foreground"
          strokeWidth="0.75"
          strokeDasharray="4 2"
        >
          {/* Горизонтальный размер нижних шкафов */}
          <motion.path
            d="M 150 430 L 650 430"
            variants={dimensionVariants}
            initial="hidden"
            animate={controls}
            custom={0}
          />
          <motion.path
            d="M 150 400 L 150 440"
            variants={dimensionVariants}
            initial="hidden"
            animate={controls}
            custom={1}
          />
          <motion.path
            d="M 650 400 L 650 440"
            variants={dimensionVariants}
            initial="hidden"
            animate={controls}
            custom={2}
          />

          {/* Вертикальный размер */}
          <motion.path
            d="M 690 120 L 690 400"
            variants={dimensionVariants}
            initial="hidden"
            animate={controls}
            custom={3}
          />
          <motion.path
            d="M 650 120 L 700 120"
            variants={dimensionVariants}
            initial="hidden"
            animate={controls}
            custom={4}
          />
          <motion.path
            d="M 650 400 L 700 400"
            variants={dimensionVariants}
            initial="hidden"
            animate={controls}
            custom={5}
          />

          {/* Размер верхних шкафов */}
          <motion.path
            d="M 150 90 L 450 90"
            variants={dimensionVariants}
            initial="hidden"
            animate={controls}
            custom={6}
          />
          <motion.path
            d="M 150 90 L 150 120"
            variants={dimensionVariants}
            initial="hidden"
            animate={controls}
            custom={7}
          />
          <motion.path
            d="M 450 90 L 450 120"
            variants={dimensionVariants}
            initial="hidden"
            animate={controls}
            custom={8}
          />
        </g>

        {/* Текст размеров */}
        <g className="fill-foreground font-mono text-[10px]">
          <motion.text
            x="400"
            y="450"
            textAnchor="middle"
            variants={textVariants}
            initial="hidden"
            animate={controls}
            custom={0}
          >
            2400 мм
          </motion.text>
          <motion.text
            x="710"
            y="265"
            textAnchor="start"
            variants={textVariants}
            initial="hidden"
            animate={controls}
            custom={1}
          >
            850 мм
          </motion.text>
          <motion.text
            x="300"
            y="80"
            textAnchor="middle"
            variants={textVariants}
            initial="hidden"
            animate={controls}
            custom={2}
          >
            1800 мм
          </motion.text>
        </g>

        {/* Точки соединений */}
        <g className="fill-foreground">
          {[
            [150, 280], [250, 280], [400, 280], [550, 280], [650, 280],
            [150, 400], [250, 400], [400, 400], [550, 400], [650, 400],
            [150, 120], [250, 120], [350, 120], [450, 120],
            [150, 220], [250, 220], [350, 220], [450, 220],
          ].map(([x, y], i) => (
            <motion.circle
              key={i}
              cx={x}
              cy={y}
              r="2"
              variants={dotVariants}
              initial="hidden"
              animate={controls}
              custom={i}
            />
          ))}
        </g>

        {/* Декоративная сетка на фоне */}
        <g className="stroke-foreground" strokeWidth="0.25" opacity="0.1">
          {Array.from({ length: 17 }, (_, i) => (
            <motion.line
              key={`h-${i}`}
              x1="100"
              y1={50 + i * 35}
              x2="700"
              y2={50 + i * 35}
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.3 }}
              transition={{ delay: 0.5 + i * 0.02, duration: 0.5 }}
            />
          ))}
          {Array.from({ length: 13 }, (_, i) => (
            <motion.line
              key={`v-${i}`}
              x1={100 + i * 50}
              y1="50"
              x2={100 + i * 50}
              y2="550"
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.3 }}
              transition={{ delay: 0.5 + i * 0.02, duration: 0.5 }}
            />
          ))}
        </g>
      </svg>
    </div>
  )
}
