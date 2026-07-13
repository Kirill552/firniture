'use client'

import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Check } from "lucide-react"

/**
 * Страница тарифов приведена к честному продуктовому обещанию (Task 3).
 * DXF и PDF после проверки. Без G-code / 30 секунд / готово для станка.
 */
const tiers = [
  {
    name: "Стартовый",
    price: "4999 ₽",
    description: "Для небольших цехов и частных мастеров.",
    features: [
      "10 заказов в месяц",
      "Базовый анализ эскиза",
      "Подбор фурнитуры",
      "DXF и PDF после проверки",
    ],
    cta: "Начать работу",
  },
  {
    name: "Профессиональный",
    price: "14999 ₽",
    description: "Для растущих мебельных фабрик.",
    features: [
      "100 заказов в месяц",
      "Продвинутый анализ и уточнения",
      "Диалог с технологом",
      "DXF и PDF для утверждённых заказов",
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
      "Полный доступ к анализу",
      "Кастомные интеграции",
      "Персональная поддержка",
    ],
    cta: "Связаться с нами",
  },
]

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-[#F5F5F1] py-12 sm:py-24 text-[#111111]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center">
          <h1 className="text-4xl md:text-5xl font-semibold tracking-tight mb-4">
            Гибкие тарифы
          </h1>
          <p className="text-lg max-w-2xl mx-auto text-[#111111]">
            DXF и PDF формируются после проверки технологом. Распознавание доступно без регистрации.
          </p>
        </div>

        <div className="mt-16 grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3">
          {tiers.map((tier) => (
            <Card key={tier.name} className={`flex flex-col h-full ${tier.popular ? 'border-[#D8352A] border-2' : 'border-[#9C9C95]'}`}>
              <CardHeader>
                <CardTitle>{tier.name}</CardTitle>
                <CardDescription>{tier.description}</CardDescription>
              </CardHeader>
              <CardContent className="flex-grow flex flex-col">
                <div className="mb-6">
                  <span className="text-4xl font-semibold">{tier.price}</span>
                  <span className="text-[#9C9C95]">{(tier.name === 'Стартовый' || tier.name === 'Профессиональный') ? '/месяц' : ''}</span>
                </div>
                <ul className="space-y-3 text-sm flex-grow">
                  {tier.features.map((feature) => (
                    <li key={feature} className="flex items-center">
                      <Check className="h-4 w-4 mr-2 flex-shrink-0" style={{ color: '#D8352A' }} />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
                <Button className="w-full mt-8" style={{ background: tier.popular ? '#111111' : undefined }}>
                  {tier.cta}
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="text-center mt-16">
          <Link href="/" className="text-sm font-medium hover:underline">
            На главную
          </Link>
        </div>
      </div>
    </div>
  )
}
