'use client'

import { useState, useEffect, Suspense } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { useRouter, useSearchParams } from 'next/navigation'
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
import { isSafeReturnUrl } from '@/lib/auth-return'

type OnboardingStep = 'welcome' | 'setup-later'

function WelcomePageInner() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const returnTo = searchParams.get("returnTo")
  const hasPendingDraft = !!returnTo && isSafeReturnUrl(returnTo)

  const [step, setStep] = useState<OnboardingStep>('welcome')
  const [factoryName, setFactoryName] = useState<string>('')

  useEffect(() => {
    const fetchFactory = async () => {
      try {
        const res = await fetch('/api/v1/auth/me')
        if (res.ok) {
          const data = await res.json()
          setFactoryName(data.factory?.name || 'вашей фабрики')
        } else {
          // Гость без сессии: показываем нейтральный текст вместо пустого имени
          setFactoryName('вашей фабрики')
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
    if (hasPendingDraft && returnTo) {
      router.push(returnTo)
    } else {
      router.push('/new')
    }
  }

  const handleSkipToOrders = () => {
    completeOnboarding()
    router.push('/orders')
  }

  const handleSetupFirst = () => {
    setStep('setup-later')
  }

  return (
    <div className="min-h-[100dvh] bg-[#f3f6f8] text-[#171a1d] flex items-center justify-center p-4 md:p-6">
      <AnimatePresence mode="wait">
        {step === 'welcome' && (
          <motion.div
            key="welcome"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="w-full max-w-4xl"
          >
            <div className="text-center mb-8 md:mb-12">
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#c7ff00]/10 text-xs font-semibold text-[#171a1d] mb-4">
                <Sparkles className="w-3.5 h-3.5" />
                Добро пожаловать в АвтоРаскрой
              </div>

              <h1 className="text-3xl md:text-5xl font-bold tracking-tight mb-4 text-[#171a1d] leading-none">
                {hasPendingDraft ? (
                  <>
                    Продолжить работу над заказом
                    <br />
                    <span className="text-[#66707a] text-2xl md:text-4xl">для {factoryName}?</span>
                  </>
                ) : (
                  <>
                    Готовы создать первый заказ
                    <br />
                    <span className="text-[#66707a] text-2xl md:text-4xl">для {factoryName}?</span>
                  </>
                )}
              </h1>

              <p className="text-sm md:text-base max-w-2xl mx-auto text-[#66707a] leading-relaxed">
                {hasPendingDraft
                  ? "Ваш гостевой черновик успешно сохранен и привязан к вашей фабрике. Перейдите к нему, чтобы просмотреть спецификацию и получить PDF/DXF чертежи."
                  : "Загрузите эскиз мебели. Система распознает размеры, построит спецификацию, сгенерирует DXF чертежи деталей и PDF карты раскроя."}
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-6 mb-8">
              <div className="md:col-span-2">
                <Card
                  className="border border-[#d7dde2] bg-white p-6 md:p-8 h-full cursor-pointer hover:border-[#c7ff00]/70 transition-all duration-200 relative group rounded-xl shadow-sm"
                  onClick={handleQuickStart}
                >
                  <div className="absolute top-4 right-4">
                    <span className="px-2.5 py-1 rounded-full bg-[#171a1d] text-white text-[10px] font-bold">
                      Рекомендуем
                    </span>
                  </div>

                  <div className="flex items-start gap-5">
                    <div className="flex-shrink-0 w-12 h-12 md:w-14 md:h-14 rounded-xl bg-[#171a1d] flex items-center justify-center">
                      <Camera className="w-6 h-6 text-white" />
                    </div>

                    <div className="flex-1">
                      <h3 className="text-lg font-bold mb-1.5 flex items-center gap-2 text-[#171a1d]">
                        {hasPendingDraft ? "Открыть сохраненный заказ" : "Быстрый старт"}
                      </h3>
                      <p className="text-xs md:text-sm text-[#66707a] leading-relaxed mb-4">
                        {hasPendingDraft
                          ? "Перейти к чертежам, интерактивному просмотру и спецификации деталей вашего сохраненного заказа."
                          : "Загрузите эскиз или фотографию деталировки. Нейросеть распознает размеры и подготовит чертежи."}
                      </p>

                      <div className="flex items-center gap-4 text-xs font-semibold text-[#171a1d]">
                        <span className="flex items-center gap-1.5">
                          <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                          {hasPendingDraft ? "Черновик уже в кабинете" : "Создать заказ за минуту"}
                        </span>
                      </div>
                    </div>

                    <div className="flex-shrink-0 self-center">
                      <div className="w-10 h-10 rounded-full bg-[#f3f6f8] group-hover:bg-[#c7ff00] transition-colors duration-150 flex items-center justify-center">
                        <ArrowRight className="w-5 h-5 text-[#171a1d]" />
                      </div>
                    </div>
                  </div>

                  <div className="mt-6 pt-6 border-t border-[#d7dde2] text-xs">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-[#66707a]">
                        <div className="w-5 h-5 rounded-full bg-[#f3f6f8] flex items-center justify-center text-[#171a1d] text-[10px] font-bold">1</div>
                        <span>Эскиз</span>
                      </div>
                      <ChevronRight className="w-3.5 h-3.5 text-[#d7dde2]" />
                      <div className="flex items-center gap-2 text-[#66707a]">
                        <div className="w-5 h-5 rounded-full bg-[#f3f6f8] flex items-center justify-center text-[#171a1d] text-[10px] font-bold">2</div>
                        <span>Параметры деталей</span>
                      </div>
                      <ChevronRight className="w-3.5 h-3.5 text-[#d7dde2]" />
                      <div className="flex items-center gap-2 text-[#66707a]">
                        <div className="w-5 h-5 rounded-full bg-[#f3f6f8] flex items-center justify-center text-[#171a1d] text-[10px] font-bold">3</div>
                        <span>Спецификация, DXF и PDF</span>
                      </div>
                    </div>
                  </div>
                </Card>
              </div>

              <Card
                className="border border-[#d7dde2] bg-white p-6 h-full cursor-pointer hover:border-[#c7ff00]/70 transition-all duration-200 rounded-xl shadow-sm flex flex-col justify-between"
                onClick={handleSetupFirst}
              >
                <div>
                  <div className="w-10 h-10 rounded-lg bg-[#f3f6f8] flex items-center justify-center mb-4 text-[#171a1d]">
                    <Settings className="w-5 h-5" />
                  </div>

                  <h3 className="text-base font-bold mb-1.5 text-[#171a1d]">Настроить фабрику</h3>
                  <p className="text-xs text-[#66707a] leading-relaxed">
                    Укажите материалы деталей, кромку и зазоры. Это можно сделать и позже в кабинете.
                  </p>
                </div>

                <span className="text-xs font-semibold flex items-center gap-1 text-[#171a1d] mt-4">
                  Параметры фабрики <ChevronRight className="w-3.5 h-3.5" />
                </span>
              </Card>
            </div>

            <div className="text-center">
              <button
                onClick={handleSkipToOrders}
                className="text-xs font-semibold text-[#66707a] hover:text-[#171a1d] transition-colors duration-150 cursor-pointer"
              >
                Пропустить и перейти к заказам →
              </button>
            </div>
          </motion.div>
        )}

        {step === 'setup-later' && (
          <motion.div
            key="setup"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="w-full max-w-xl"
          >
            <Card className="p-6 md:p-8 bg-white border border-[#d7dde2] rounded-xl shadow-sm">
              <div className="text-center mb-6">
                <div className="w-12 h-12 rounded-xl bg-[#c7ff00]/10 flex items-center justify-center mx-auto mb-4 text-[#171a1d]">
                  <Factory className="w-6 h-6" />
                </div>
                <h2 className="text-xl font-bold text-[#171a1d] mb-1">Быстрая настройка</h2>
                <p className="text-xs text-[#66707a]">Все параметры можно изменить позже в профиле фабрики</p>
              </div>

              <div className="space-y-3 mb-6">
                {[
                  { icon: FileText, label: 'Материалы деталей', desc: 'Установите ЛДСП по умолчанию (16 мм / 18 мм)' },
                  { icon: Settings, label: 'Генерация спецификации', desc: 'Зазоры для сборки и параметры кромки' },
                  { icon: Wrench, label: 'Экспорт чертежей', desc: 'Форматирование DXF деталей' },
                ].map((item, i) => (
                  <div key={i} className="flex items-center gap-4 p-4 rounded-xl bg-[#f3f6f8] border border-[#d7dde2]/40">
                    <div className="w-10 h-10 rounded-lg bg-white flex items-center justify-center text-[#171a1d] border border-[#d7dde2]/30">
                      <item.icon className="w-5 h-5" />
                    </div>
                    <div className="flex-1">
                      <div className="text-sm font-semibold text-[#171a1d]">{item.label}</div>
                      <div className="text-[11px] text-[#66707a]">{item.desc}</div>
                    </div>
                    <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
                  </div>
                ))}
              </div>

              <div className="flex gap-3">
                <Button 
                  variant="outline" 
                  className="flex-1 h-10 border-[#d7dde2] hover:bg-[#f3f6f8] text-[#171a1d] font-semibold active:scale-[0.98] transition-all duration-150 rounded-lg cursor-pointer" 
                  onClick={() => setStep('welcome')}
                >
                  Назад
                </Button>
                <Button
                  className="flex-1 h-10 bg-[#c7ff00] hover:bg-[#aee600] text-[#171a1d] font-semibold active:scale-[0.98] transition-all duration-150 rounded-lg cursor-pointer"
                  onClick={() => {
                    completeOnboarding()
                    router.push('/settings')
                  }}
                >
                  Настройки <ArrowRight className="w-4 h-4 ml-1.5" />
                </Button>
              </div>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default function WelcomePage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-[100dvh] bg-[#f3f6f8]">
        <div className="text-sm text-[#66707a]">Загрузка...</div>
      </div>
    }>
      <WelcomePageInner />
    </Suspense>
  )
}
