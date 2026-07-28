import type { Metadata } from 'next'
import Link from 'next/link'
import { Check } from 'lucide-react'
import { buttonVariants } from '@/components/ui/button-variants'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { LEGAL } from '@/lib/legal'

export const metadata: Metadata = {
  title: 'Цены',
  description:
    'Идёт открытая бета: спецификация, DXF и PDF выгружаются без оплаты и без лимита на число заказов. Оплата в сервисе отключена.',
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
        text: 'Сейчас нисколько. Идёт открытая бета: спецификация, DXF и PDF выгружаются без оплаты, ограничения на число заказов нет. Оплата в сервисе отключена.',
      },
    },
    {
      '@type': 'Question',
      name: 'Почему сервис бесплатный?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'Расчёт дорабатывается по замечаниям технологов с производства. Пока в цифрах остаются ошибки, брать за них деньги неправильно, поэтому доступ открыт всем.',
      },
    },
    {
      '@type': 'Question',
      name: 'Когда появится оплата?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'Даты не называем. О платных тарифах предупредим заранее письмом и на этой странице. Единицей тарификации останется заказ целиком, сколько бы изделий в нём ни было.',
      },
    },
  ],
}

/** Что открыто в бете. */
const BETA_FEATURES = [
  'Спецификация панелей, кромки и фурнитуры',
  'DXF раскроя и PDF карты раскроя',
  'Сколько угодно заказов — счётчика нет',
  'Без карты, без подписки и без автосписаний',
]

/**
 * Цены. На время открытой беты оплата отключена, тарифов нет.
 */
export default function PricingPage() {
  return (
    <div className="min-h-screen bg-[#f3f6f8] py-12 sm:py-24 text-[#171a1d]">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }}
      />
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center">
          <span className="inline-flex items-center gap-2 rounded-full border border-[#d7dde2] bg-white px-3 py-1.5 text-xs font-semibold uppercase tracking-[1.5px] text-[#66707a]">
            <span className="h-2 w-2 rounded-full bg-[#c7ff00]" />
            Открытая бета
          </span>
          <h1 className="mt-6 text-4xl md:text-5xl font-semibold tracking-tight mb-4">
            Сейчас бесплатно
          </h1>
          <p className="text-lg max-w-2xl mx-auto">
            Расчёт дорабатывается по замечаниям технологов с производства. Пока правим цифры,
            деньги не берём: спецификация, DXF и PDF доступны без оплаты и без ограничения
            по количеству заказов.
          </p>
        </div>

        <div className="mt-12 mx-auto max-w-2xl">
          <Card className="border-2 border-[#171a1d]">
            <CardHeader>
              <CardTitle>Что открыто в бете</CardTitle>
              <CardDescription>
                Полный цикл: от эскиза до файлов для производства.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="mb-6 text-4xl font-semibold">0 ₽</p>
              <ul className="space-y-3 text-sm">
                {BETA_FEATURES.map((feature) => (
                  <li key={feature} className="flex items-start">
                    <Check
                      className="h-4 w-4 mr-2 mt-0.5 flex-shrink-0"
                      style={{ color: '#171a1d' }}
                    />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>

        <div className="mt-10 text-center">
          <Link href="/new" className={buttonVariants({ size: 'lg' })}>
            Загрузить эскиз
          </Link>
        </div>

        <section className="mt-20 mx-auto max-w-3xl space-y-6 text-[15px] leading-relaxed">
          <div>
            <h2 className="text-xl font-semibold mb-2">Что станет платным потом</h2>
            <p>
              Когда расчёт перестанет требовать правок, выгрузка файлов станет платной:
              единица тарификации — заказ целиком, сколько бы изделий в нём ни было.
              Даты не называем, о цене предупредим заранее письмом и на этой странице.
            </p>
          </div>
          <div>
            <h2 className="text-xl font-semibold mb-2">Что считается одним заказом</h2>
            <p>
              Заказ — это то, что вы выгружаете целиком: кухонный гарнитур из восьми модулей
              и одна тумба считаются одинаково. Мы не считаем изделия, панели или листы.
            </p>
          </div>
          <div>
            <h2 className="text-xl font-semibold mb-2">Повторное скачивание</h2>
            <p>
              Доступ к ревизии заказа остаётся за вами: скачивайте DXF и PDF заново
              сколько угодно раз — с другого компьютера, после переустановки, через полгода.
            </p>
          </div>
          <div>
            <h2 className="text-xl font-semibold mb-2">Если в файлах ошибка</h2>
            <p>
              В бете платежи не проводятся, возвращать нечего. Нашли расхождение размеров
              или выгрузка не сработала — напишите на{' '}
              <a className="font-semibold underline" href={`mailto:${LEGAL.email}`}>
                {LEGAL.email}
              </a>
              , пересчитаем заказ и починим расчёт. Для платного периода останется возврат
              100% в течение 7 дней — условия в{' '}
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
