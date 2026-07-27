import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Статьи о мебельном производстве',
  description:
    'Практические гайды для мебельных технологов: раскрой ЛДСП, присадка фурнитуры, кромка, спецификации, DXF для производства.',
  openGraph: {
    type: 'article',
    locale: 'ru_RU',
    url: '/blog',
    siteName: 'АвтоРаскрой',
    title: 'Статьи о мебельном производстве — АвтоРаскрой',
    description: 'Практические гайды для мебельных технологов: раскрой ЛДСП, присадка фурнитуры, кромка, спецификации, DXF для производства.',
    images: [{ url: '/og-blog.jpg', width: 1200, height: 630, alt: 'АвтоРаскрой' }],
  },
  twitter: {
    card: 'summary_large_image',
    images: ['/og-blog.jpg'],
  },
};

/** Статьи блога. Порядок — от новых к старым. */
const ARTICLES = [
  {
    slug: 'dxf-dlya-chpu',
    title: 'DXF для ЧПУ: версия формата, слои и подготовка файла',
    description:
      'R12 или R2013, слои под контур и присадку, единицы измерения, замкнутые контуры. И где в цепочке появляется G-code.',
    date: '2026-07-26',
    dateLabel: '26 июля 2026',
    minutes: 6,
  },
  {
    slug: 'specifikaciya-mebeli',
    title: 'Спецификация мебели: что в неё входит и как её собрать',
    description:
      'Деталировка, кромление, фурнитура, крепёж и итоги. Что требует ГОСТ, что нужно цеху и как не потерять ревизию.',
    date: '2026-07-24',
    dateLabel: '24 июля 2026',
    minutes: 7,
  },
  {
    slug: 'kromka-pvh-tolshchina',
    title: 'Толщина кромки ПВХ: 0,4, 1 и 2 мм — где какую клеить',
    description:
      'Куда идёт каждая толщина, как вычитать кромку из размера детали и сколько метров ленты заказывать на корпус.',
    date: '2026-07-21',
    dateLabel: '21 июля 2026',
    minutes: 6,
  },
  {
    slug: 'karta-raskroya-ldsp',
    title: 'Карта раскроя ЛДСП: как составить и получить онлайн',
    description:
      'Пропил 3,2–4,4 мм, припуски на кромку, направление текстуры, процент использования листа 2800×2070.',
    date: '2026-07-17',
    dateLabel: '17 июля 2026',
    minutes: 7,
  },
  {
    slug: 'prisadka-petel',
    title: 'Присадка петель: схема разметки под мебельные петли 35 мм',
    description:
      'Отступ K от края фасада, система 32 мм, глубина чашки, количество петель по высоте и весу двери.',
    date: '2026-07-12',
    dateLabel: '12 июля 2026',
    minutes: 6,
  },
] as const;

/** Индекс статей блога. */
export default function BlogIndexPage() {
  return (
    <main className="min-h-screen bg-[#f3f6f8] text-[#171a1d]">
      <div className="mx-auto max-w-[900px] px-6 py-16">
        <nav className="text-[12px] text-[#66707a]">
          <Link href="/" className="hover:text-[#171a1d]">Главная</Link>
          <span className="mx-2">/</span>
          <span>Статьи</span>
        </nav>

        <h1 className="mt-6 text-[32px] md:text-[38px] font-extrabold tracking-[-1px]">
          Статьи для мебельных технологов
        </h1>
        <p className="mt-4 max-w-[52ch] text-[15px] text-[#66707a] leading-relaxed">
          Разборы производственных тем: раскрой, кромка, присадка, спецификации,
          подготовка файлов для станка.
        </p>

        <div className="mt-10 grid gap-5 md:grid-cols-2">
          {ARTICLES.map((a) => (
            <Link
              key={a.slug}
              href={`/blog/${a.slug}`}
              className="group border border-[#d7dde2] bg-white rounded-xl p-6 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
            >
              <div className="font-mono text-[10px] uppercase tracking-[2px] text-[#66707a]">
                <time dateTime={a.date}>{a.dateLabel}</time> · {a.minutes} мин
              </div>
              <h2 className="mt-3 text-[17px] font-bold leading-snug text-[#171a1d] group-hover:underline underline-offset-4">
                {a.title}
              </h2>
              <p className="mt-2 text-[13px] leading-relaxed text-[#66707a]">
                {a.description}
              </p>
            </Link>
          ))}
        </div>
      </div>
    </main>
  );
}
