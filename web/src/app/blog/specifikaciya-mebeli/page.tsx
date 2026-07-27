import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Спецификация мебели: что в неё входит и как собрать',
  description:
    'Из чего состоит спецификация мебельного изделия: деталировка панелей, кромка, фурнитура, крепёж. Что требует ГОСТ, что нужно цеху и как не потерять ревизию.',
  alternates: { canonical: '/blog/specifikaciya-mebeli' },
  openGraph: {
    type: 'article',
    locale: 'ru_RU',
    url: '/blog/specifikaciya-mebeli',
    siteName: 'АвтоРаскрой',
    title: 'Спецификация мебели: что в неё входит и как собрать — АвтоРаскрой',
    description: 'Из чего состоит спецификация мебельного изделия: деталировка панелей, кромка, фурнитура, крепёж. Что требует ГОСТ, что нужно цеху и как не потерять ревизию.',
    images: [{ url: '/og-blog.jpg', width: 1200, height: 630, alt: 'АвтоРаскрой' }],
  },
  twitter: {
    card: 'summary_large_image',
    images: ['/og-blog.jpg'],
  },
};

const articleJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'Article',
  headline: 'Спецификация мебели: что в неё входит и как её собрать',
  description:
    'Состав спецификации мебельного изделия: панели, кромка, фурнитура, крепёж, ревизии и передача в цех.',
  author: { '@type': 'Organization', name: 'АвтоРаскрой' },
  publisher: { '@type': 'Organization', name: 'АвтоРаскрой' },
  datePublished: '2026-07-24',
  inLanguage: 'ru',
};

const faqJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: [
    {
      '@type': 'Question',
      name: 'Что входит в спецификацию мебели?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'Деталировка панелей с размерами и материалом, стороны и толщина кромки, фурнитура с артикулами, крепёж, а также итоги: количество деталей, площадь плиты в м² и метраж кромки.',
      },
    },
    {
      '@type': 'Question',
      name: 'Обязательно ли оформлять спецификацию по ГОСТ?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'ГОСТ 16371-2014 требует, чтобы мебель делали по утверждённой технической документации, но форму документа не задаёт. Если предприятие работает по ЕСКД, спецификацию оформляют по ГОСТ 2.106. Для заказной мебели форма обычно своя.',
      },
    },
    {
      '@type': 'Question',
      name: 'Чем спецификация отличается от карты раскроя?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'Спецификация отвечает на вопрос «что из чего состоит»: перечень деталей и фурнитуры. Карта раскроя показывает, как эти детали лягут на лист ЛДСП. Карта строится из спецификации, а не наоборот.',
      },
    },
  ],
};

/**
 * Статья «Спецификация мебели» — кластер ~780 показов/мес (Wordstat: «спецификация мебели» 776).
 * Состав BOM и статусы ревизий описаны по реальной модели: api/schemas.py, api/models.py.
 */
export default function SpecifikaciyaMebeliPage() {
  return (
    <main className="min-h-screen bg-[#f3f6f8] text-[#171a1d]">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(articleJsonLd) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }}
      />
      <div className="mx-auto max-w-[760px] px-6 py-16">
        <nav className="text-[12px] text-[#66707a]">
          <Link href="/" className="hover:text-[#171a1d]">Главная</Link>
          <span className="mx-2">/</span>
          <Link href="/blog" className="hover:text-[#171a1d]">Статьи</Link>
          <span className="mx-2">/</span>
          <span>Спецификация мебели</span>
        </nav>

        <h1 className="mt-6 text-[32px] md:text-[38px] font-extrabold leading-[1.05] tracking-[-1px]">
          Спецификация мебели: что в неё входит и как её собрать
        </h1>
        <p className="mt-3 text-[13px] text-[#66707a]">24 июля 2026 · 7 мин чтения</p>

        <div className="mt-10 space-y-8 text-[15px] leading-relaxed">
          <p>
            Спецификация отвечает на один вопрос: из чего состоит изделие.
            Перечень деталей с размерами и материалом, кромка, фурнитура,
            крепёж. Без неё нельзя ни посчитать заказ, ни отдать его в цех:
            раскройщику нужны габариты панелей, снабженцу — артикулы петель,
            сборщику — что и куда крепится.
          </p>

          <section>
            <h2 className="mb-3 text-[20px] font-bold">Обязательный минимум</h2>
            <table className="w-full text-[14px] border border-[#d7dde2] bg-white rounded-xl overflow-hidden">
              <thead>
                <tr className="text-left text-[#66707a] border-b border-[#d7dde2]">
                  <th className="py-2 px-4">Раздел</th>
                  <th className="py-2 px-4">Что в нём</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-[#d7dde2]">
                  <td className="py-2 px-4">Деталировка</td>
                  <td className="py-2 px-4">Название панели, длина × ширина, толщина, материал, количество, направление текстуры</td>
                </tr>
                <tr className="border-b border-[#d7dde2]">
                  <td className="py-2 px-4">Кромление</td>
                  <td className="py-2 px-4">Какие торцы кромятся и какой толщиной ленты</td>
                </tr>
                <tr className="border-b border-[#d7dde2]">
                  <td className="py-2 px-4">Фурнитура</td>
                  <td className="py-2 px-4">Петли, направляющие, полкодержатели, ручки: артикул, производитель, количество</td>
                </tr>
                <tr className="border-b border-[#d7dde2]">
                  <td className="py-2 px-4">Крепёж</td>
                  <td className="py-2 px-4">Конфирматы, эксцентрики, шканты, саморезы</td>
                </tr>
                <tr>
                  <td className="py-2 px-4">Итоги</td>
                  <td className="py-2 px-4">Число деталей, площадь плиты в м², метраж кромки по толщинам</td>
                </tr>
              </tbody>
            </table>
          </section>

          <section>
            <h2 className="mb-3 text-[20px] font-bold">Что говорит ГОСТ</h2>
            <p>
              ГОСТ 16371-2014 «Мебель. Общие технические условия» обязывает
              изготовителя работать по утверждённой технической документации,
              но саму форму спецификации не описывает. Если на предприятии
              принята ЕСКД, документ оформляют по ГОСТ 2.106 с разделами
              «Детали», «Стандартные изделия», «Материалы». Заказная мебель
              обычно живёт по внутренней форме цеха: важно не оформление,
              а полнота данных.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-[20px] font-bold">Ревизии: где теряются деньги</h2>
            <p>
              Заказчик передвинул полку, технолог поправил высоту, а в цех ушла
              старая версия. Пилят по одному файлу, сверлят по другому. Чтобы
              этого не было, у спецификации должен быть номер версии и статус.
            </p>
            <p>
              В АвтоРаскрое спецификация проходит четыре состояния: черновик,
              проверена, утверждена, отклонена. Экспорт DXF и PDF открывается
              только для утверждённой ревизии. Любая правка размеров поднимает
              номер, а попытка сохранить поверх чужой версии возвращает ошибку
              вместо тихой перезаписи.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-[20px] font-bold">Частые дыры в спецификации</h2>
            <ul className="list-disc space-y-2 pl-6">
              <li>
                Нет направления текстуры. Раскройщик развернёт деталь ради
                экономии, и фасады пойдут полосами в разные стороны.
              </li>
              <li>
                Размеры без учёта кромки. Про вычитание 2&nbsp;мм подробно
                в статье о{' '}
                <Link href="/blog/kromka-pvh-tolshchina" className="underline underline-offset-4">
                  толщине кромки ПВХ
                </Link>
                .
              </li>
              <li>
                Фурнитура без артикулов. «Петля накладная» ничего не говорит:
                у разных производителей отличаются присадочные размеры.
              </li>
              <li>
                Нет крепежа. Конфирматы и эксцентрики забывают чаще всего,
                а без них сборка встаёт.
              </li>
              <li>
                Одна общая цифра площади без разбивки по материалам. Белый
                корпус и цветные фасады закупаются отдельно.
              </li>
            </ul>
          </section>

          <section className="border border-[#d7dde2] bg-white rounded-xl p-6">
            <h2 className="mb-3 text-[20px] font-bold">Как это работает в АвтоРаскрое</h2>
            <p>
              Из фото эскиза сервис собирает деталировку: панели с размерами,
              флаги кромления по сторонам, подобранная по каталогу фурнитура
              с артикулами и точки присадки. Итоги считаются сами: число
              панелей, площадь в м², длина кромки. После утверждения ревизии
              спецификация уходит в DXF и в{' '}
              <Link href="/blog/karta-raskroya-ldsp" className="underline underline-offset-4">
                карту раскроя
              </Link>
              .
            </p>
            <Link
              href="/new"
              className="mt-4 inline-flex items-center gap-2 rounded-xl bg-[#171a1d] px-6 py-3 text-[14px] font-bold text-white hover:bg-black transition-colors"
            >
              Собрать спецификацию по эскизу →
            </Link>
          </section>
        </div>
      </div>
    </main>
  );
}
