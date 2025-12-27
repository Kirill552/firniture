"use client"
import { motion } from 'framer-motion'
import { staggerContainer } from '@/lib/motion'
import { ReactNode } from 'react'

interface Props { children: ReactNode; delay?: number; stagger?: number; className?: string }

export function StaggerContainer({ children, delay=0.05, stagger=0.07, className }: Props) {
  return (
    <motion.div
      className={className}
      variants={staggerContainer(stagger, delay)}
      initial="hidden"
      animate="show"
    >
      {children}
    </motion.div>
  )
}
