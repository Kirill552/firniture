'use client'

import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import { ArrowRight } from 'lucide-react'
import { ThemeToggle } from '@/components/theme-toggle'
import { LazyBlueprintAnimation } from '@/components/lazy'

export default function LandingPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-background relative overflow-hidden">
      {/* Кнопка переключения темы */}
      <div className="absolute top-4 right-4 z-20">
        <ThemeToggle />
      </div>

      {/* Анимированный чертёж на фоне */}
      <LazyBlueprintAnimation />

      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: 'easeOut' }}
        className="text-center z-10 px-4"
      >
        <h1 className="text-5xl md:text-7xl font-bold text-foreground mb-4">
          Мебель-ИИ
        </h1>
        <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-8">
          Облачная AI-SaaS платформа для автоматизации мебельного производства.
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, delay: 0.5, type: 'spring', stiffness: 120 }}
        className="z-10 flex flex-col items-center gap-4"
      >
        <Link href="/login" passHref>
          <Button
            size="lg"
            className="rounded-full text-lg px-8 py-6 shadow-lg hover:shadow-xl transition-all duration-300 group"
          >
            Войти
            <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform duration-300" />
          </Button>
        </Link>
        <Link
          href="/pricing"
          className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
        >
          Посмотреть тарифы
        </Link>
      </motion.div>
    </div>
  )
}
