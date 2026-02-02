'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import {
  Camera,
  FileText,
  Wrench,
  ArrowRight,
  CheckCircle2,
  Sparkles,
  Play,
  Clock,
  Zap,
  ChevronRight,
  Upload,
  Settings,
  Factory
} from 'lucide-react'

// Этапы онбординга
type OnboardingStep = 'welcome' | 'quick-start' | 'setup-later'

export default function WelcomePage() {
  const router = useRouter()
  const [step, setStep] = useState<OnboardingStep>('welcome')
  const [factoryName, setFactoryName] = useState<string>('')

  useEffect(() => {
    // Получаем имя фабрики из API (упрощённо)
    const fetchFactory = async () => {
      try {
        const res = await fetch('/api/v1/auth/me')
        if (res.ok) {
          const data = await res.json()
          setFactoryName(data.factory?.name || 'вашей фабрики')
        }
      } catch {
        setFactoryName('вашей фабрики')
      }
    }
    fetchFactory()
  }, [])

  // Пометить онбординг как пройденный
  const completeOnboarding = () => {
    localStorage.setItem('onboarding_completed', 'true')
  }

  const handleQuickStart = () => {
    completeOnboarding()
    router.push('/new')
  }

  const handleSkipToOrders = () => {
    completeOnboarding()
    router.push('/orders')
  }

  const handleSetupFirst = () => {
    setStep('setup-later')
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 via-orange-50 to-yellow-50 dark:from-neutral-950 dark:via-neutral-900 dark:to-neutral-950">
      {/* Декоративные элементы */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 left-10 w-72 h-72 bg-amber-200/30 dark:bg-amber-900/10 rounded-full blur-3xl" />
        <div className="absolute bottom-20 right-10 w-96 h-96 bg-orange-200/30 dark:bg-orange-900/10 rounded-full blur-3xl" />
        {/* Сетка как на чертеже */}
        <svg className="absolute inset-0 w-full h-full opacity-[0.03] dark:opacity-[0.02]" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="currentColor" strokeWidth="1"/>
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
        </svg>
      </div>

      <div className="relative z-10 flex items-center justify-center min-h-screen p-6">
        <AnimatePresence mode="wait">
          {step === 'welcome' && (
            <motion.div
              key="welcome"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.4 }}
              className="w-full max-w-4xl"
            >
              {/* Заголовок */}
              <div className="text-center mb-12">
                <motion.div
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ delay: 0.1, type: 'spring', stiffness: 200 }}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 text-sm font-medium mb-6"
                >
                  <Sparkles className="w-4 h-4" />
                  Добро пожаловать в АвтоРаскрой
                </motion.div>

                <motion.h1
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 }}
                  className="text-4xl md:text-5xl font-bold text-neutral-900 dark:text-white mb-4"
                >
                  Готовы создать первый заказ
                  <br />
                  <span className="text-amber-600 dark:text-amber-400">для {factoryName}?</span>
                </motion.h1>

                <motion.p
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                  className="text-lg text-neutral-600 dark:text-neutral-400 max-w-2xl mx-auto"
                >
                  Загрузите фото эскиза — и через 30 секунд получите
                  готовые файлы для станка ЧПУ
                </motion.p>
              </div>

              {/* Три опции */}
              <div className="grid md:grid-cols-3 gap-6 mb-8">
                {/* Быстрый старт — основной CTA */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4 }}
                  className="md:col-span-2"
                >
                  <Card
                    className="relative overflow-hidden border-2 border-amber-200 dark:border-amber-800 bg-white dark:bg-neutral-900 p-8 h-full cursor-pointer group hover:border-amber-400 dark:hover:border-amber-600 transition-all duration-300 hover:shadow-xl hover:shadow-amber-100 dark:hover:shadow-amber-900/20"
                    onClick={handleQuickStart}
                  >
                    {/* Бейдж "Рекомендуем" */}
                    <div className="absolute top-4 right-4">
                      <span className="px-3 py-1 rounded-full bg-amber-500 text-white text-xs font-semibold">
                        Рекомендуем
                      </span>
                    </div>

                    <div className="flex items-start gap-6">
                      <div className="flex-shrink-0 w-16 h-16 rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center shadow-lg shadow-amber-200 dark:shadow-amber-900/30">
                        <Camera className="w-8 h-8 text-white" />
                      </div>

                      <div className="flex-1">
                        <h3 className="text-xl font-semibold text-neutral-900 dark:text-white mb-2 flex items-center gap-2">
                          Быстрый старт
                          <Zap className="w-5 h-5 text-amber-500" />
                        </h3>
                        <p className="text-neutral-600 dark:text-neutral-400 mb-4">
                          Загрузите фото чертежа или эскиза — ИИ автоматически извлечёт размеры,
                          подберёт фурнитуру и создаст файлы для станка
                        </p>

                        <div className="flex items-center gap-4 text-sm text-neutral-500 dark:text-neutral-500">
                          <span className="flex items-center gap-1">
                            <Clock className="w-4 h-4" />
                            ~30 секунд
                          </span>
                          <span className="flex items-center gap-1">
                            <CheckCircle2 className="w-4 h-4 text-green-500" />
                            Без настройки
                          </span>
                        </div>
                      </div>

                      <div className="flex-shrink-0 self-center">
                        <div className="w-12 h-12 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center group-hover:bg-amber-200 dark:group-hover:bg-amber-800/40 transition-colors">
                          <ArrowRight className="w-6 h-6 text-amber-600 dark:text-amber-400 group-hover:translate-x-1 transition-transform" />
                        </div>
                      </div>
                    </div>

                    {/* Мини-демо шаги */}
                    <div className="mt-6 pt-6 border-t border-neutral-100 dark:border-neutral-800">
                      <div className="flex items-center justify-between text-sm">
                        <div className="flex items-center gap-2 text-neutral-500">
                          <div className="w-6 h-6 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center text-amber-600 dark:text-amber-400 text-xs font-bold">1</div>
                          <span>Фото эскиза</span>
                        </div>
                        <ChevronRight className="w-4 h-4 text-neutral-300" />
                        <div className="flex items-center gap-2 text-neutral-500">
                          <div className="w-6 h-6 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center text-amber-600 dark:text-amber-400 text-xs font-bold">2</div>
                          <span>ИИ анализ</span>
                        </div>
                        <ChevronRight className="w-4 h-4 text-neutral-300" />
                        <div className="flex items-center gap-2 text-neutral-500">
                          <div className="w-6 h-6 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center text-amber-600 dark:text-amber-400 text-xs font-bold">3</div>
                          <span>DXF + G-code</span>
                        </div>
                      </div>
                    </div>
                  </Card>
                </motion.div>

                {/* Альтернатива: настроить сначала */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.5 }}
                >
                  <Card
                    className="border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-6 h-full cursor-pointer group hover:border-neutral-300 dark:hover:border-neutral-700 transition-all duration-300"
                    onClick={handleSetupFirst}
                  >
                    <div className="w-12 h-12 rounded-xl bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center mb-4 group-hover:bg-neutral-200 dark:group-hover:bg-neutral-700 transition-colors">
                      <Settings className="w-6 h-6 text-neutral-600 dark:text-neutral-400" />
                    </div>

                    <h3 className="text-lg font-semibold text-neutral-900 dark:text-white mb-2">
                      Сначала настроить
                    </h3>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
                      Указать станок, материалы по умолчанию и параметры генерации
                    </p>

                    <span className="text-sm text-amber-600 dark:text-amber-400 flex items-center gap-1 group-hover:gap-2 transition-all">
                      Настройки
                      <ChevronRight className="w-4 h-4" />
                    </span>
                  </Card>
                </motion.div>
              </div>

              {/* Ссылка "Пропустить" */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.6 }}
                className="text-center"
              >
                <button
                  onClick={handleSkipToOrders}
                  className="text-sm text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300 transition-colors"
                >
                  Пропустить и перейти к заказам →
                </button>
              </motion.div>
            </motion.div>
          )}

          {step === 'setup-later' && (
            <motion.div
              key="setup"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.4 }}
              className="w-full max-w-2xl"
            >
              <Card className="p-8 bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800">
                <div className="text-center mb-8">
                  <div className="w-16 h-16 rounded-2xl bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center mx-auto mb-4">
                    <Factory className="w-8 h-8 text-amber-600 dark:text-amber-400" />
                  </div>
                  <h2 className="text-2xl font-bold text-neutral-900 dark:text-white mb-2">
                    Быстрая настройка
                  </h2>
                  <p className="text-neutral-600 dark:text-neutral-400">
                    Можно настроить позже в разделе "Настройки"
                  </p>
                </div>

                {/* Чеклист что можно настроить */}
                <div className="space-y-4 mb-8">
                  {[
                    { icon: Wrench, label: 'Профиль станка', desc: 'Weihong, Syntec, FANUC...' },
                    { icon: FileText, label: 'Материалы по умолчанию', desc: 'ЛДСП 16мм, кромка ПВХ' },
                    { icon: Settings, label: 'Параметры генерации', desc: 'Размер листа, отступы' },
                  ].map((item, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-4 p-4 rounded-xl bg-neutral-50 dark:bg-neutral-800/50"
                    >
                      <div className="w-10 h-10 rounded-lg bg-white dark:bg-neutral-800 flex items-center justify-center shadow-sm">
                        <item.icon className="w-5 h-5 text-neutral-600 dark:text-neutral-400" />
                      </div>
                      <div className="flex-1">
                        <div className="font-medium text-neutral-900 dark:text-white">{item.label}</div>
                        <div className="text-sm text-neutral-500">{item.desc}</div>
                      </div>
                      <CheckCircle2 className="w-5 h-5 text-neutral-300 dark:text-neutral-600" />
                    </div>
                  ))}
                </div>

                <div className="flex gap-3">
                  <Button
                    variant="outline"
                    className="flex-1"
                    onClick={() => setStep('welcome')}
                  >
                    Назад
                  </Button>
                  <Button
                    className="flex-1 bg-amber-500 hover:bg-amber-600"
                    onClick={() => {
                      completeOnboarding()
                      router.push('/settings')
                    }}
                  >
                    Открыть настройки
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </Button>
                </div>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
