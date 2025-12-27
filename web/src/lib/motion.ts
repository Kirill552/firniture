import { Variants, Transition } from 'framer-motion'

// Универсальные transition пресеты
export const fast: Transition = { duration: 0.15, ease: [0.4, 0, 0.2, 1] }
export const base: Transition = { duration: 0.25, ease: [0.4, 0, 0.2, 1] }
export const slow: Transition = { duration: 0.4, ease: [0.4, 0, 0.2, 1] }

// Простое появление с лёгким смещением
export const fadeInUp: Variants = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: base },
}

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: base },
}

export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.96 },
  show: { opacity: 1, scale: 1, transition: { ...base, duration: 0.2 } },
}

// Контейнер для stagger вложенных motion.* компонентов
export const staggerContainer = (stagger: number = 0.06, delayChildren: number = 0): Variants => ({
  hidden: {},
  show: {
    transition: {
      staggerChildren: stagger,
      delayChildren,
    },
  },
})

// Динамический генератор slide variants
export const slide = (direction: 'left'|'right'|'up'|'down' = 'up', distance = 24): Variants => {
  const map: Record<string, any> = {
    up: { y: distance },
    down: { y: -distance },
    left: { x: distance },
    right: { x: -distance },
  }
  return {
    hidden: { opacity: 0, ...map[direction] },
    show: { opacity: 1, x: 0, y: 0, transition: base },
    exit: { opacity: 0, ...map[direction], transition: fast },
  }
}

export const springSoft: Transition = { type: 'spring', stiffness: 220, damping: 24, mass: 0.9 }
export const springBouncy: Transition = { type: 'spring', stiffness: 360, damping: 20, mass: 0.7 }

// Хелпер для композиции motion props
export const combine = (...objs: any[]) => objs.reduce((acc, o) => Object.assign(acc, o), {})
