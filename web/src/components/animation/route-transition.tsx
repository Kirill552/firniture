"use client"
import { usePathname } from 'next/navigation'
import { AnimatePresence, motion } from 'framer-motion'
import { ReactNode } from 'react'
import { slide } from '@/lib/motion'

interface RouteTransitionProps {
  children: ReactNode
}

// Глобальные переходы между страницами (уровень layout)
export function RouteTransition({ children }: RouteTransitionProps) {
  const pathname = usePathname()
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={pathname}
        variants={slide('up', 24)}
        initial="hidden"
        animate="show"
        exit="exit"
        style={{ minHeight: '100%' }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  )
}
