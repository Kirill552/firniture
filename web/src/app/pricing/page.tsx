'use client'

import { motion } from "framer-motion"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Check } from "lucide-react"
import Link from "next/link"

const tiers = [
  {
    name: "Стартовый",
    price: "4999 ₽",
    description: "Для небольших цехов и частных мастеров.",
    features: [
      "10 заказов в месяц",
      "Базовый AI-анализ ТЗ",
      "Подбор фурнитуры (RAG)",
      "Генерация DXF",
    ],
    cta: "Начать работу",
  },
  {
    name: "Профессиональный",
    price: "14999 ₽",
    description: "Для растущих мебельных фабрик.",
    features: [
      "100 заказов в месяц",
      "Продвинутый AI-анализ",
      "Диалог с AI-технологом",
      "Генерация DXF и G-code",
      "Интеграция с 1С (базовая)",
    ],
    cta: "Выбрать тариф",
    popular: true,
  },
  {
    name: "Энтерпрайз",
    price: "По запросу",
    description: "Для крупных производств с особыми требованиями.",
    features: [
      "Безлимитные заказы",
      "Полный доступ к AI",
      "Кастомные интеграции",
      "Персональная поддержка",
      "3D-визуализация в реальном времени",
    ],
    cta: "Связаться с нами",
  },
]

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.2,
      delayChildren: 0.3,
    },
  },
}

const itemVariants = {
  hidden: { y: 20, opacity: 0 },
  visible: { y: 0, opacity: 1, transition: { type: "spring", stiffness: 100 } },
}

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-black py-12 sm:py-24">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-center"
        >
          <h1 className="text-4xl md:text-5xl font-bold bg-clip-text text-transparent bg-gradient-to-b from-neutral-800 to-neutral-500 dark:from-neutral-200 dark:to-neutral-400 mb-4">
            Гибкие тарифы для вашего бизнеса
          </h1>
          <p className="text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
            Выберите план, который идеально подходит для автоматизации вашего производства.
          </p>
        </motion.div>

        <motion.div 
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="mt-16 grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3"
        >
          {tiers.map((tier) => (
            <motion.div key={tier.name} variants={itemVariants}>
              <Card className={`flex flex-col h-full ${tier.popular ? 'border-primary border-2' : ''}`}>
                <CardHeader>
                  <CardTitle>{tier.name}</CardTitle>
                  <CardDescription>{tier.description}</CardDescription>
                </CardHeader>
                <CardContent className="flex-grow flex flex-col">
                  <div className="mb-6">
                    <span className="text-4xl font-bold">{tier.price}</span>
                    <span className="text-gray-500">{tier.name === 'Стартовый' || tier.name === 'Профессиональный' ? '/месяц' : ''}</span>
                  </div>
                  <ul className="space-y-3 text-sm flex-grow">
                    {tier.features.map((feature) => (
                      <li key={feature} className="flex items-center">
                        <Check className="h-4 w-4 text-green-500 mr-2 flex-shrink-0" />
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                  <Button className={`w-full mt-8 ${tier.popular ? '' : 'variant-"outline"'}`}>{tier.cta}</Button>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </motion.div>
         <div className="text-center mt-16">
            <Link href="/" className="text-sm font-medium text-primary hover:underline">
                Назад на главную
            </Link>
        </div>
      </div>
    </div>
  )
}
