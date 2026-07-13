'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { useRouter } from 'next/navigation'
import {
  Camera,
  FileText,
  Wrench,
  ArrowRight,
  CheckCircle2,
  Sparkles,
  ChevronRight,
  Settings,
  Factory
} from 'lucide-react'

type OnboardingStep = 'welcome' | 'setup-later'

/**
 * Страница приветствия обновлена по Task 3: удалены обещания про 30 секунд и готовность для станка.
 * DXF и PDF после входа и проверки технологом.
 */
export default function WelcomePage() {
  const router = useRouter()
  const [step, setStep] = useState<OnboardingStep>('welcome')
  const [factoryName, setFactoryName] = useState<string>('')

  useEffect(() => {
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
    <div className="min-h-screen bg-[#F5F5F1] text-[#111111]">
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
              <div className="text-center mb-12">
                <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#E9E9E4] text-sm font-medium mb-6">
                  <Sparkles className="w-4 h-4" />
                  Добро пожаловать в АвтоРаскрой
                </div>

                <h1 className="text-4xl md:text-5xl font-semibold tracking-tight mb-4">
                  Готовы создать первый заказ
                  <br />
                  <span className="text-[#D8352A]">для {factoryName}?</span>
                </h1>

                <p className="text-lg max-w-2xl mx-auto text-[#111111]">
                  Загрузите эскиз. Получите распознанные параметры и уточнения. После проверки технологом — DXF и PDF.
                </p>
              </div>

              <div className="grid md:grid-cols-3 gap-6 mb-8">
                <div className="md:col-span-2">
                  <Card
                    className="border-2 border-[#D8352A] bg-white p-8 h-full cursor-pointer"
                    onClick={handleQuickStart}
                  >
                    <div className="absolute top-4 right-4">
                      <span className="px-3 py-1 rounded-full bg-[#D8352A] text-white text-xs font-semibold">Рекомендуем</span>
                    </div>

                    <div className="flex items-start gap-6">
                      <div className="flex-shrink-0 w-16 h-16 rounded-2xl bg-[#111111] flex items-center justify-center">
                        <Camera className="w-8 h-8 text-white" />
                      </div>

                      <div className="flex-1">
                        <h3 className="text-xl font-semibold mb-2 flex items-center gap-2">
                          Быстрый старт
                        </h3>
                        <p className="mb-4">
                          Загрузите эскиз — распознавание и предварительная проверка без регистрации.
                          DXF и PDF после входа и утверждения заказа технологом.
                        </p>

                        <div className="flex items-center gap-4 text-sm text-[#9C9C95]">
                          <span className="flex items-center gap-1">
                            <CheckCircle2 className="w-4 h-4 text-[#D8352A]" />
                            Распознавание без регистрации
                          </span>
                        </div>
                      </div>

                      <div className="flex-shrink-0 self-center">
                        <div className="w-12 h-12 rounded-full bg-[#E9E9E4] flex items-center justify-center">
                          <ArrowRight className="w-6 h-6 text-[#111111]" />
                        </div>
                      </div>
                    </div>

                    <div className="mt-6 pt-6 border-t border-[#E9E9E4] text-sm">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-[#9C9C95]">
                          <div className="w-6 h-6 rounded-full bg-[#E9E9E4] flex items-center justify-center text-[#111111] text-xs font-bold">1</div>
                          <span>Эскиз</span>
                        </div>
                        <ChevronRight className="w-4 h-4 text-[#9C9C95]" />
                        <div className="flex items-center gap-2 text-[#9C9C95]">
                          <div className="w-6 h-6 rounded-full bg-[#E9E9E4] flex items-center justify-center text-[#111111] text-xs font-bold">2</div>
                          <span>Параметры и уточнения</span>
                        </div>
                        <ChevronRight className="w-4 h-4 text-[#9C9C95]" />
                        <div className="flex items-center gap-2 text-[#9C9C95]">
                          <div className="w-6 h-6 rounded-full bg-[#E9E9E4] flex items-center justify-center text-[#111111] text-xs font-bold">3</div>
                          <span>DXF и PDF</span>
                        </div>
                      </div>
                    </div>
                  </Card>
                </div>

                <Card
                  className="border border-[#9C9C95] bg-white p-6 h-full cursor-pointer"
                  onClick={handleSetupFirst}
                >
                  <div className="w-12 h-12 rounded-xl bg-[#E9E9E4] flex items-center justify-center mb-4">
                    <Settings className="w-6 h-6" />
                  </div>

                  <h3 className="text-lg font-semibold mb-2">Сначала настроить</h3>
                  <p className="text-sm text-[#9C9C95] mb-4">
                    Указать материалы и параметры. Можно позже.
                  </p>

                  <span className="text-sm flex items-center gap-1 text-[#D8352A]">
                    Настройки <ChevronRight className="w-4 h-4" />
                  </span>
                </Card>
              </div>

              <div className="text-center">
                <button
                  onClick={handleSkipToOrders}
                  className="text-sm text-[#9C9C95] hover:text-[#111111]"
                >
                  Пропустить и перейти к заказам →
                </button>
              </div>
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
              <Card className="p-8 bg-white border border-[#9C9C95]">
                <div className="text-center mb-8">
                  <div className="w-16 h-16 rounded-2xl bg-[#E9E9E4] flex items-center justify-center mx-auto mb-4">
                    <Factory className="w-8 h-8" />
                  </div>
                  <h2 className="text-2xl font-semibold mb-2">Быстрая настройка</h2>
                  <p className="text-[#9C9C95]">Можно настроить позже в разделе «Настройки»</p>
                </div>

                <div className="space-y-4 mb-8">
                  {[
                    { icon: Wrench, label: 'Профиль станка', desc: 'Weihong, Syntec, FANUC...' },
                    { icon: FileText, label: 'Материалы по умолчанию', desc: 'ЛДСП 16 мм' },
                    { icon: Settings, label: 'Параметры', desc: 'Размер листа, отступы' },
                  ].map((item, i) => (
                    <div key={i} className="flex items-center gap-4 p-4 rounded bg-[#F5F5F1]">
                      <div className="w-10 h-10 rounded-lg bg-white flex items-center justify-center">
                        <item.icon className="w-5 h-5" />
                      </div>
                      <div className="flex-1">
                        <div className="font-medium">{item.label}</div>
                        <div className="text-sm text-[#9C9C95]">{item.desc}</div>
                      </div>
                      <CheckCircle2 className="w-5 h-5 text-[#9C9C95]" />
                    </div>
                  ))}
                </div>

                <div className="flex gap-3">
                  <Button variant="outline" className="flex-1" onClick={() => setStep('welcome')}>Назад</Button>
                  <Button
                    className="flex-1"
                    onClick={() => {
                      completeOnboarding()
                      router.push('/settings')
                    }}
                  >
                    Открыть настройки <ArrowRight className="w-4 h-4 ml-2" />
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
