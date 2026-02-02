'use client'

import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import {
  ArrowRight,
  Camera,
  MessageSquare,
  FileCode,
  Cpu,
  Package,
  Zap,
  CheckCircle2
} from 'lucide-react'
import { ThemeToggle } from '@/components/theme-toggle'

const fadeIn = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 }
}

const steps = [
  {
    icon: Camera,
    title: 'Загрузите эскиз',
    description: 'Фото чертежа или ТЗ — система извлечёт размеры автоматически'
  },
  {
    icon: MessageSquare,
    title: 'ИИ уточнит детали',
    description: 'Диалог с технологом: материал, фурнитура, особенности сборки'
  },
  {
    icon: FileCode,
    title: 'Получите файлы',
    description: 'DXF для раскроя и G-code для вашего станка — готово к производству'
  }
]

const features = [
  {
    icon: Camera,
    title: 'Vision OCR',
    description: 'Распознавание размеров и параметров с фото эскизов и чертежей'
  },
  {
    icon: Package,
    title: 'Каталог Boyard 2024',
    description: '1300+ позиций фурнитуры с умным подбором по параметрам изделия'
  },
  {
    icon: Zap,
    title: 'G-code генерация',
    description: 'Программы ЧПУ под ваш станок с учётом профиля и инструмента'
  }
]

const machines = [
  'Weihong NK105/NK260',
  'Syntec 6MB',
  'FANUC 0i-MF',
  'DSP A11/A18',
  'HOMAG woodWOP'
]

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 border-b border-border/40 bg-background/80 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center text-primary-foreground font-bold">
              А
            </div>
            <span className="font-semibold">АвтоРаскрой</span>
          </div>
          <div className="flex items-center gap-4">
            <ThemeToggle />
            <Link href="/login">
              <Button variant="ghost" size="sm">Войти</Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="pt-32 pb-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <motion.div
            initial="hidden"
            animate="visible"
            variants={fadeIn}
            transition={{ duration: 0.5 }}
          >
            <p className="text-sm font-medium text-primary mb-4">
              Для технологов мебельных производств
            </p>
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-foreground mb-6 leading-tight">
              Фото эскиза → файлы для станка
              <br />
              <span className="text-muted-foreground">за 30 секунд</span>
            </h1>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-8">
              ИИ-технолог извлекает параметры из чертежа, подбирает фурнитуру
              и генерирует файлы для вашего станка ЧПУ
            </p>
          </motion.div>

          <motion.div
            initial="hidden"
            animate="visible"
            variants={fadeIn}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4"
          >
            <Link href="/new">
              <Button size="lg" className="text-base px-8 h-12 group">
                Попробовать бесплатно
                <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
              </Button>
            </Link>
            <Link href="/login">
              <Button variant="outline" size="lg" className="text-base px-8 h-12">
                Войти
              </Button>
            </Link>
          </motion.div>

          <motion.p
            initial="hidden"
            animate="visible"
            variants={fadeIn}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="mt-6 text-sm text-muted-foreground"
          >
            Экономия 2-3 часов на каждый заказ
          </motion.p>
        </div>
      </section>

      {/* Как это работает */}
      <section className="py-20 px-6 bg-muted/30">
        <div className="max-w-5xl mx-auto">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={fadeIn}
            className="text-center mb-12"
          >
            <h2 className="text-2xl md:text-3xl font-bold mb-4">Как это работает</h2>
            <p className="text-muted-foreground">Три шага от эскиза до готовых файлов</p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-8">
            {steps.map((step, index) => (
              <motion.div
                key={step.title}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true }}
                variants={fadeIn}
                transition={{ delay: index * 0.1 }}
                className="relative"
              >
                <div className="bg-background border border-border rounded-xl p-6 h-full">
                  <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
                    <step.icon className="h-6 w-6 text-primary" />
                  </div>
                  <div className="text-sm font-medium text-muted-foreground mb-2">
                    Шаг {index + 1}
                  </div>
                  <h3 className="text-lg font-semibold mb-2">{step.title}</h3>
                  <p className="text-muted-foreground text-sm">{step.description}</p>
                </div>
                {index < steps.length - 1 && (
                  <div className="hidden md:block absolute top-1/2 -right-4 transform -translate-y-1/2">
                    <ArrowRight className="h-5 w-5 text-muted-foreground/40" />
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Возможности */}
      <section className="py-20 px-6">
        <div className="max-w-5xl mx-auto">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={fadeIn}
            className="text-center mb-12"
          >
            <h2 className="text-2xl md:text-3xl font-bold mb-4">Возможности</h2>
            <p className="text-muted-foreground">Всё что нужно для автоматизации расчётов</p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-6">
            {features.map((feature, index) => (
              <motion.div
                key={feature.title}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true }}
                variants={fadeIn}
                transition={{ delay: index * 0.1 }}
                className="border border-border rounded-xl p-6 hover:border-primary/50 transition-colors"
              >
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
                  <feature.icon className="h-5 w-5 text-primary" />
                </div>
                <h3 className="font-semibold mb-2">{feature.title}</h3>
                <p className="text-muted-foreground text-sm">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Совместимость */}
      <section className="py-20 px-6 bg-muted/30">
        <div className="max-w-4xl mx-auto text-center">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={fadeIn}
          >
            <div className="flex items-center justify-center gap-2 mb-4">
              <Cpu className="h-5 w-5 text-primary" />
              <h2 className="text-2xl md:text-3xl font-bold">Совместимые станки</h2>
            </div>
            <p className="text-muted-foreground mb-8">
              Генерируем G-code под профиль вашего оборудования
            </p>
          </motion.div>

          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={fadeIn}
            transition={{ delay: 0.1 }}
            className="flex flex-wrap items-center justify-center gap-3"
          >
            {machines.map((machine) => (
              <div
                key={machine}
                className="flex items-center gap-2 bg-background border border-border rounded-full px-4 py-2"
              >
                <CheckCircle2 className="h-4 w-4 text-green-600" />
                <span className="text-sm font-medium">{machine}</span>
              </div>
            ))}
          </motion.div>

          <motion.p
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={fadeIn}
            transition={{ delay: 0.2 }}
            className="mt-6 text-sm text-muted-foreground"
          >
            Не нашли свой станок? Напишите нам — добавим профиль
          </motion.p>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-6">
        <div className="max-w-2xl mx-auto text-center">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={fadeIn}
          >
            <h2 className="text-2xl md:text-3xl font-bold mb-4">
              Готовы автоматизировать расчёты?
            </h2>
            <p className="text-muted-foreground mb-8">
              Регистрация бесплатная. Первые 10 заказов — без ограничений.
            </p>
            <Link href="/new">
              <Button size="lg" className="text-base px-8 h-12 group">
                Начать бесплатно
                <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
              </Button>
            </Link>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-8 px-6">
        <div className="max-w-5xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded bg-primary flex items-center justify-center text-primary-foreground font-bold text-xs">
              А
            </div>
            <span className="text-sm text-muted-foreground">
              АвтоРаскрой © 2026
            </span>
          </div>
          <div className="flex items-center gap-6 text-sm text-muted-foreground">
            <Link href="/pricing" className="hover:text-foreground transition-colors">
              Тарифы
            </Link>
            <a href="mailto:support@avtoraskroy.ru" className="hover:text-foreground transition-colors">
              support@avtoraskroy.ru
            </a>
          </div>
        </div>
      </footer>
    </div>
  )
}
