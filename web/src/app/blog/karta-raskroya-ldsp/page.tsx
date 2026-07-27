import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Карта раскроя ЛДСП: как составить и получить онлайн — АвтоРаскрой',
  description:
    'Что такое карта раскроя, как считать пропил и припуск на кромку, почему деталь не влезает в лист 2800×2070 и как получить карту раскроя ЛДСП онлайн из эскиза.',
  alternates: { canonical: '/blog/karta-raskroya-ldsp' },
  openGraph: {
    type: 'article',
    locale: 'ru_RU',
    url: '/blog/karta-raskroya-ldsp',
    siteName: 'АвтоРаскрой',
    title: 'Карта раскроя ЛДСП: как составить и получить онлайн — АвтоРаскрой',
    description: 'Что такое карта раскроя, как считать пропил и припуск на кромку, почему деталь не влезает в лист 2800×2070 и как получить карту раскроя ЛДСП онлайн из эскиза.',
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
  headline: 'Карта раскроя ЛДСП: как составить и получить онлайн',
  description:
    'Карта раскроя ЛДСП: пропил 4 мм, припуск на кромку, направление текстуры, процент использования листа 2800×2070.',
  author: { '@type': 'Organization', name: 'АвтоРаскрой' },
  publisher: { '@type': 'Organization', name: 'АвтоРаскрой' },
  datePublished: '2026-07-17',
  inLanguage: 'ru',
};

const faqJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: [
    {
      '@type': 'Question',
      name: 'Что такое карта раскроя ЛДСП?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'Карта раскроя — схема размещения деталей на листе ЛДСП с учётом пропила пилы, направления текстуры и припусков на кромку. По ней пилят на форматно-раскроечном станке и считают расход материала.',
      },
    },
    {
      '@type': 'Question',
      name: 'Какой зазор закладывать на пропил?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'Пропил основного пильного диска на форматно-раскроечном станке обычно 3,2–4,4 мм. В карте раскроя закладывают 4 мм между деталями и по краю листа, на крупных производствах доходит до 6 мм.',
      },
    },
    {
      '@type': 'Question',
      name: 'Какой стандартный размер листа ЛДСП?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'Самый ходовой формат — 2800×2070 мм при толщине 16 мм, он есть и у Egger, и у Kronospan. У Kronospan дополнительно идут 2750×1830 и 2620×1830. Полезная площадь меньше габарита: край листа обрезают.',
      },
    },
  ],
};

/**
 * Статья «Карта раскроя ЛДСП» — кластер ~3000 показов/мес (Wordstat:
 * «карта раскроя» 1581, «раскрой ЛДСП онлайн» 1500, «программа для раскроя ЛДСП» 504).
 * Числа взяты из констант проекта (api/constants.py) — то, что реально считает сервис.
 */
export default function KartaRaskroyaPage() {
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
          <span>Карта раскроя ЛДСП</span>
        </nav>

        <h1 className="mt-6 text-[32px] md:text-[38px] font-extrabold leading-[1.05] tracking-[-1px]">
          Карта раскроя ЛДСП: как составить и получить онлайн
        </h1>
        <p className="mt-3 text-[13px] text-[#66707a]">17 июля 2026 · 7 мин чтения</p>

        <div className="mt-10 space-y-8 text-[15px] leading-relaxed">
          <p>
            Карта раскроя — это схема, по которой пильщик режет лист. На ней
            видно, какая деталь где лежит, куда идёт текстура и сколько
            материала уходит в обрезки. Ошибка на этапе карты стоит целого
            листа: деталь «влезала» в расчёте, но не влезла с учётом пропила.
          </p>

          <section>
            <h2 className="mb-3 text-[20px] font-bold">Что такое карта раскроя</h2>
            <p>
              Это лист с габаритом 2800×2070&nbsp;мм (формат ЛДСП 16&nbsp;мм,
              который есть и у Egger, и у Kronospan), на котором размещены
              прямоугольники деталей с подписями: имя, размер, количество.
              Между деталями стоит зазор на пропил. Дополнительно на карте
              указывают направление текстуры и стороны под кромку. У Kronospan
              в ходу ещё 2750×1830 и 2620×1830, так что формат листа стоит
              уточнять до раскладки, а не после.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-[20px] font-bold">Пропил: почему 4 мм, а не ноль</h2>
            <p>
              Пильный диск съедает материал. У основного диска форматно-раскроечного
              станка пропил обычно 3,2–4,4&nbsp;мм, подрезной настраивают на
              0,1–0,3&nbsp;мм шире, иначе на нижней пласти пойдут сколы. Если
              разложить детали вплотную, каждая вторая окажется уже на толщину реза.
              Рабочий зазор в карте: 4&nbsp;мм между деталями и по краю листа,
              на крупных производствах закладывают до 6&nbsp;мм с запасом на торцовку.
            </p>
            <div className="mt-4 border border-[#d7dde2] bg-white rounded-xl p-5">
              <div className="font-mono text-[11px] uppercase tracking-[2px] text-[#66707a] mb-3">
                Проверка на пальцах
              </div>
              <p className="text-[14px]">
                Две детали по 1400&nbsp;мм в лист 2800&nbsp;мм не влезут:
                1400 + 4 + 1400 = 2804&nbsp;мм. Нужно либо 1398&nbsp;мм, либо
                вторая деталь уезжает на следующий лист.
              </p>
            </div>
          </section>

          <section>
            <h2 className="mb-3 text-[20px] font-bold">Припуски: кромка, полки, ящики</h2>
            <table className="w-full text-[14px] border border-[#d7dde2] bg-white rounded-xl overflow-hidden">
              <thead>
                <tr className="text-left text-[#66707a] border-b border-[#d7dde2]">
                  <th className="py-2 px-4">Что считаем</th>
                  <th className="py-2 px-4">Типовое значение</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-[#d7dde2]">
                  <td className="py-2 px-4">Пропил (kerf)</td>
                  <td className="py-2 px-4">4 мм</td>
                </tr>
                <tr className="border-b border-[#d7dde2]">
                  <td className="py-2 px-4">Кромка ПВХ</td>
                  <td className="py-2 px-4">0,4–2 мм на сторону</td>
                </tr>
                <tr className="border-b border-[#d7dde2]">
                  <td className="py-2 px-4">Зазор полки в корпусе</td>
                  <td className="py-2 px-4">3 мм с каждой стороны</td>
                </tr>
                <tr className="border-b border-[#d7dde2]">
                  <td className="py-2 px-4">Зазор под ящик (направляющие)</td>
                  <td className="py-2 px-4">26 мм (13 мм на сторону)</td>
                </tr>
                <tr>
                  <td className="py-2 px-4">Отступ задней стенки</td>
                  <td className="py-2 px-4">10 мм</td>
                </tr>
              </tbody>
            </table>
            <p className="mt-3">
              Кромку 2&nbsp;мм на видимую сторону обязательно вычитают из
              размера детали, иначе фасад не встанет в проём. Кромку 0,4&nbsp;мм
              на скрытых торцах обычно не вычитают.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-[20px] font-bold">Направление текстуры</h2>
            <p>
              У ЛДСП с рисунком «дерево» текстура идёт вдоль длинной стороны
              листа. Детали фасадов и боковин разворачивать нельзя, иначе на
              собранном корпусе полосы пойдут поперёк. Расплата за текстуру
              составляет 5–15% полезной площади: алгоритм не может повернуть
              деталь на 90°, чтобы уплотнить раскладку.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-[20px] font-bold">Сколько материала уходит в отход</h2>
            <p>
              Нормальный процент использования листа для кухонного корпуса
              лежит в диапазоне 70–85%. Ниже 60% бывает в двух случаях: мало
              деталей на лист при единичном заказе либо раскладка без поворотов.
              Считается это просто: сумма площадей деталей делится на площадь
              листа. На карте процент печатают, по нему заказчику выставляют
              материал.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-[20px] font-bold">Частые ошибки</h2>
            <ul className="list-disc space-y-2 pl-6">
              <li>
                Нулевой пропил. Раскладка впритык съедает по детали с каждого
                листа.
              </li>
              <li>
                Размер по чертежу без кромки. Деталь 596&nbsp;мм с кромкой
                2×2&nbsp;мм станет 600&nbsp;мм и не влезет в проём.
              </li>
              <li>
                Поворот детали с текстурой ради экономии 3% материала. Итог:
                переделка фасада за свой счёт.
              </li>
              <li>
                Нет припуска по краю листа. Кромка листа бывает битой,
                закладывайте отступ 10 мм.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="mb-3 text-[20px] font-bold">Как получить карту раскроя онлайн</h2>
            <p>
              Классический путь — забить размеры руками в программу раскроя.
              АвтоРаскрой убирает этот шаг: загружаете фото или PDF эскиза,
              сервис распознаёт габариты изделия, разбивает его на детали
              (боковины, дно, полки, фасады), подбирает фурнитуру и раскладывает
              панели на листе. На выходе — PDF карты раскроя с размерами и
              процентом использования и DXF для станка. Про сверловку под
              фурнитуру — в статье{' '}
              <Link href="/blog/prisadka-petel" className="underline underline-offset-4">
                «Присадка петель»
              </Link>
              .
            </p>
          </section>

          <section className="border border-[#d7dde2] bg-white rounded-xl p-6">
            <h2 className="mb-3 text-[20px] font-bold">Попробовать на своём эскизе</h2>
            <p>
              Загрузите фото наброска — получите спецификацию панелей, карту
              раскроя в PDF и DXF с контурами и точками присадки.
            </p>
            <Link
              href="/new"
              className="mt-4 inline-flex items-center gap-2 rounded-xl bg-[#171a1d] px-6 py-3 text-[14px] font-bold text-white hover:bg-black transition-colors"
            >
              Загрузить эскиз →
            </Link>
          </section>
        </div>
      </div>
    </main>
  );
}
