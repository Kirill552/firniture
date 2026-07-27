import type { Metadata } from 'next'
import Link from 'next/link'
import { Check } from 'lucide-react'
import { buttonVariants } from '@/components/ui/button-variants'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { LEGAL } from '@/lib/legal'

export const metadata: Metadata = {
  title: 'Цены — АвтоРаскрой',
  description:
    'Первый заказ бесплатно, дальше 890 ₽ за заказ целиком. Пакет 10 заказов — 7900 ₽, кредиты не сгорают. Повторное скачивание оплаченного заказа бесплатно.',
  alternates: { canonical: '/pricing' },
}

const faqJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: [
    {
      '@type': 'Question',
      name: 'Сколько стоит выгрузка заказа?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: '890 ₽ за заказ целиком — сколько бы изделий в нём ни было. Первый заказ каждой фабрики бесплатный. Пакет из 10 заказов стоит 7900 ₽, это 790 ₽ за заказ, и кредиты не сгорают.',
      },
    },
    {
      '@type': 'Question',
      name: 'Можно ли вернуть деньги за заказ?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'Да. Возврат 100% в течение 7 дней, если в выданном файле ошибка в размерах или выгрузка не сработала. Сначала бесплатно пересчитаем заказ; если это не помогло — вернём деньги на карту в течение 10 рабочих дней.',
      },
    },
    {
      '@type': 'Question',
      name: 'Какими способами можно оплатить?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'Оплата проходит через ЮKassa: банковской картой или через СБП. Платежи принимаются от физических лиц, чек формируется в сервисе «Мой налог» и приходит на указанную почту.',
      },
    },
  ],
}

const PLANS = [
  {
    name: 'Первый заказ',
    price: 'Бесплатно',
    description: 'Один раз для каждой фабрики — чтобы проверить файлы на своём станке.',
    features: [
      'DXF раскроя и PDF карты раскроя',
      'Спецификация панелей, кромки и фурнитуры',
      'Без карты и без автосписаний',
    ],
  },
  {
    name: 'Заказ',
    price: '890 ₽',
    description: 'За заказ целиком, сколько бы изделий в нём ни было.',
    features: [
      'Оплата картой или через СБП',
      'Повторное скачивание той же ревизии — бесплатно',
      'Платите только за те заказы, которые выгружаете',
    ],
    highlighted: true,
  },
  {
    name: 'Пакет 10 заказов',
    price: '7900 ₽',
    description: '790 ₽ за заказ. Кредиты не сгорают.',
    features: [
      'Списывается по одному при выгрузке заказа',
      'Без срока действия и без автопродления',
      'Остаток виден в карточке заказа',
    ],
  },
]

/**
 * Цены. Единица тарификации одна — заказ целиком. Подписок и тарифных планов нет.
 */
export default function PricingPage() {
  return (
    <div className="min-h-screen bg-[#F5F5F1] py-12 sm:py-24 text-[#111111]">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }}
      />
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center">
          <h1 className="text-4xl md:text-5xl font-semibold tracking-tight mb-4">
            Платите за заказ, а не за месяц
          </h1>
          <p className="text-lg max-w-2xl mx-auto">
            Распознавание эскиза и проверка спецификации бесплатны и доступны без регистрации.
            Деньги берём только за выгрузку файлов для производства.
          </p>
        </div>

        <div className="mt-16 grid grid-cols-1 gap-8 md:grid-cols-3">
          {PLANS.map((plan) => (
            <Card
              key={plan.name}
              className={`flex flex-col h-full ${plan.highlighted ? 'border-[#D8352A] border-2' : 'border-[#9C9C95]'}`}
            >
              <CardHeader>
                <CardTitle>{plan.name}</CardTitle>
                <CardDescription>{plan.description}</CardDescription>
              </CardHeader>
              <CardContent className="flex-grow flex flex-col">
                <p className="mb-6 text-4xl font-semibold">{plan.price}</p>
                <ul className="space-y-3 text-sm flex-grow">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-start">
                      <Check className="h-4 w-4 mr-2 mt-0.5 flex-shrink-0" style={{ color: '#D8352A' }} />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="mt-10 text-center">
          <Link href="/new" className={buttonVariants({ size: 'lg' })}>
            Загрузить эскиз
          </Link>
        </div>

        <section className="mt-20 mx-auto max-w-3xl space-y-6 text-[15px] leading-relaxed">
          <div>
            <h2 className="text-xl font-semibold mb-2">Что считается одним заказом</h2>
            <p>
              Заказ — это то, что вы выгружаете целиком: кухонный гарнитур из восьми модулей
              и одна тумба стоят одинаково. Мы не считаем изделия, панели или листы.
            </p>
          </div>
          <div>
            <h2 className="text-xl font-semibold mb-2">Повторное скачивание бесплатно</h2>
            <p>
              Оплата открывает доступ к ревизии заказа навсегда: скачивайте DXF и PDF заново
              сколько угодно раз — с другого компьютера, после переустановки, через полгода.
            </p>
          </div>
          <div>
            <h2 className="text-xl font-semibold mb-2">Возврат</h2>
            <p>
              Если в выданном файле ошибка в размерах или выгрузка не сработала — вернём 100%
              в течение 7 дней. Сначала бесплатно пересчитаем; деньги возвращаем на карту до
              10 рабочих дней. Пишите на{' '}
              <a className="font-semibold underline" href={`mailto:${LEGAL.email}`}>
                {LEGAL.email}
              </a>
              . Условия — в{' '}
              <Link href="/oferta" className="font-semibold underline">
                оферте
              </Link>
              .
            </p>
          </div>
        </section>

        <div className="text-center mt-16">
          <Link href="/" className="text-sm font-medium hover:underline">
            На главную
          </Link>
        </div>
      </div>
    </div>
  )
}
