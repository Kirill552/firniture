'use client'

import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import { ArrowRight } from 'lucide-react' // Assuming you have lucide-react installed

export default function LandingPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-grid-small-black/[0.2] dark:bg-grid-small-white/[0.2] relative">
      {/* Radial gradient for the container to give a faded look */}
      <div className="absolute pointer-events-none inset-0 flex items-center justify-center dark:bg-black bg-white [mask-image:radial-gradient(ellipse_at_center,transparent_20%,black)]"></div>
      
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: 'easeOut' }}
        className="text-center z-10"
      >
        <h1 className="text-5xl md:text-7xl font-bold bg-clip-text text-transparent bg-gradient-to-b from-neutral-50 to-neutral-400 bg-opacity-50 mb-4">
          Мебель-ИИ
        </h1>
        <p className="text-lg md:text-xl text-neutral-400 max-w-2xl mx-auto mb-8">
          Облачная AI-SaaS платформа для автоматизации мебельного производства.
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, delay: 0.5, type: 'spring', stiffness: 120 }}
        className="z-10"
      >
        <Link href="/login" passHref>
          <Button 
            size="lg"
            className="bg-white dark:bg-black text-black dark:text-white border-neutral-200 dark:border-slate-800 border-2 rounded-full text-lg px-8 py-6 shadow-lg hover:shadow-xl transition-shadow duration-300 group"
          >
            Войти
            <motion.div
              initial={{ x: 0 }}
              whileHover={{ x: 5 }}
              transition={{ type: 'spring', stiffness: 300 }}
              className="ml-2 group-hover:translate-x-1 transition-transform duration-300"
            >
              <ArrowRight className="h-5 w-5" />
            </motion.div>
          </Button>
        </Link>
        <div className="mt-8">
            <Link href="/pricing" className="text-sm font-medium text-neutral-400 hover:text-white transition-colors">
                Посмотреть тарифы
            </Link>
        </div>
      </motion.div>
    </div>
  )
}
