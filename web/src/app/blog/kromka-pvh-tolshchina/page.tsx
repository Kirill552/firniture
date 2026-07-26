import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Толщина кромки ПВХ: 0,4, 1 и 2 мм — где какую клеить — АвтоРаскрой',
  description:
    'Чем отличается кромка ПВХ 0,4, 1 и 2 мм, куда какую ставят, как вычитать её из размера детали и сколько метров кромки уйдёт на корпус. С расчётом на примере.',
  alternates: { canonical: '/blog/kromka-pvh-tolshchina' },
};

const articleJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'Article',
  headline: 'Толщина кромки ПВХ: 0,4, 1 и 2 мм — где какую клеить',
  description:
    'Разбор толщин кромки ПВХ для ЛДСП: применение 0,4 / 1 / 2 мм, вычитание из размера детали, расчёт метража.',
  author: { '@type': 'Organization', name: 'АвтоРаскрой' },
  publisher: { '@type': 'Organization', name: 'АвтоРаскрой' },
  datePublished: '2026-07-21',
  inLanguage: 'ru',
};

const faqJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: [
    {
      '@type': 'Question',
      name: 'Какую толщину кромки ПВХ выбрать?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'Скрытые торцы (внутренние полки, перегородки, задняя стенка) кромят лентой 0,4 мм. Видимые, но не изнашиваемые торцы — 1 мм. Фасады, столешницы и открытые полки, за которые постоянно берутся руками, — 2 мм.',
      },
    },
    {
      '@type': 'Question',
      name: 'Нужно ли вычитать толщину кромки из размера детали?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'Кромку 2 мм вычитают: деталь пилят на 4 мм меньше, если кромятся оба противоположных торца. Кромку 0,4 мм обычно не вычитают, погрешность укладывается в зазоры сборки.',
      },
    },
    {
      '@type': 'Question',
      name: 'Какой ширины бывает кромочная лента?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'Под плиту 16 мм берут ленту 19 или 22 мм: припуск нужен, чтобы кромкооблицовочный станок или фрезер снял свесы заподлицо с пластью.',
      },
    },
  ],
};

/**
 * Статья «Толщина кромки ПВХ» — кластер ~1400 показов/мес (Wordstat: «кромка пвх толщина» 1427).
 * Значения по умолчанию взяты из api/constants.py: 0,4 / 1,0 / 2,0 мм.
 */
export default function KromkaPvhPage() {
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
          <span>Толщина кромки ПВХ</span>
        </nav>

        <h1 className="mt-6 text-[32px] md:text-[38px] font-extrabold leading-[1.05] tracking-[-1px]">
          Толщина кромки ПВХ: 0,4, 1 и 2&nbsp;мм — где какую клеить
        </h1>
        <p className="mt-3 text-[13px] text-[#66707a]">21 июля 2026 · 6 мин чтения</p>

        <div className="mt-10 space-y-8 text-[15px] leading-relaxed">
          <p>
            Толщину кромки выбирают не по красоте, а по тому, кто и как будет
            трогать торец. Внутренняя полка шкафа переживёт и 0,4&nbsp;мм.
            Столешница с лентой 0,4&nbsp;мм отколется в первый год. Ниже
            разбор трёх ходовых толщин и того, как они меняют размер детали
            в раскрое.
          </p>

          <section>
            <h2 className="mb-3 text-[20px] font-bold">Три толщины и их места</h2>
            <table className="w-full text-[14px] border border-[#d7dde2] bg-white rounded-xl overflow-hidden">
              <thead>
                <tr className="text-left text-[#66707a] border-b border-[#d7dde2]">
                  <th className="py-2 px-4">Толщина</th>
                  <th className="py-2 px-4">Куда</th>
                  <th className="py-2 px-4">Почему</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-[#d7dde2]">
                  <td className="py-2 px-4">0,4 мм</td>
                  <td className="py-2 px-4">Внутренние полки, перегородки, царги, задняя стенка</td>
                  <td className="py-2 px-4">Дёшево, торец закрыт от влаги, ударов там нет</td>
                </tr>
                <tr className="border-b border-[#d7dde2]">
                  <td className="py-2 px-4">1 мм</td>
                  <td className="py-2 px-4">Видимые торцы корпуса, офисные столы</td>
                  <td className="py-2 px-4">Держит удар, но не выглядит рамкой</td>
                </tr>
                <tr>
                  <td className="py-2 px-4">2 мм</td>
                  <td className="py-2 px-4">Фасады, столешницы, открытые полки</td>
                  <td className="py-2 px-4">Снимается фаска, торец не колется от ногтей и посуды</td>
                </tr>
              </tbody>
            </table>
            <p className="mt-3">
              В расчётах АвтоРаскроя те же значения стоят по умолчанию:
              0,4&nbsp;мм для скрытых торцов, 1&nbsp;мм для видимых, 2&nbsp;мм
              для фасадов.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-[20px] font-bold">Ширина ленты: почему 19 мм при плите 16</h2>
            <p>
              Лента шире плиты специально. Кромкооблицовочный станок клеит её
              с запасом, а потом фрезы снимают свесы сверху и снизу заподлицо
              с пластью. Под ЛДСП 16&nbsp;мм берут 19 или 22&nbsp;мм, под
              столешницу 38&nbsp;мм — 42&nbsp;мм и шире.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-[20px] font-bold">Как кромка меняет размер детали</h2>
            <p>
              Кромка добавляется к габариту. Если фасад должен встать в проём
              600&nbsp;мм и кромится по всем четырём торцам лентой 2&nbsp;мм,
              панель пилят 596&nbsp;мм: 596 + 2 + 2 = 600. Забыли вычесть,
              и фасад не закрывается, а зазоры между соседними фасадами
              съедаются.
            </p>
            <div className="mt-4 border border-[#d7dde2] bg-white rounded-xl p-5 text-[14px]">
              <div className="font-mono text-[11px] uppercase tracking-[2px] text-[#66707a] mb-3">
                Правило вычитания
              </div>
              <p>
                Ленту 2&nbsp;мм вычитают всегда. Толщину 1&nbsp;мм считают на
                ответственных стыках: фасады, вставки между стенками. Про
                0,4&nbsp;мм обычно забывают сознательно, потому что 0,8&nbsp;мм
                на деталь съедаются зазорами сборки.
              </p>
            </div>
          </section>

          <section>
            <h2 className="mb-3 text-[20px] font-bold">Сколько метров кромки заказывать</h2>
            <p>
              Метраж считают по периметру кромящихся сторон, а не по периметру
              деталей. Боковина 720×500&nbsp;мм с кромкой только по переднему
              торцу даёт 0,72&nbsp;м, а не 2,44&nbsp;м. Дальше складывают все
              стороны по каждой толщине отдельно, потому что заказывают ленту
              бухтами разного типа. Запас на подрезку и брак приклейки: 5–10%.
            </p>
            <p>
              В спецификации сервиса длина кромки считается автоматически по
              флагам сторон каждой панели и выводится отдельной строкой в метрах.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-[20px] font-bold">Что ещё влияет на результат</h2>
            <ul className="list-disc space-y-2 pl-6">
              <li>
                Цвет ленты подбирают под декор конкретного производителя плиты.
                Кромка «под Egger H1180» и «дуб сонома» другого завода дадут
                видимую разницу на торце.
              </li>
              <li>
                Ручная приклейка утюгом держится хуже станочной: клей-расплав
                нужно прогреть равномерно, иначе лента отходит углами.
              </li>
              <li>
                Радиус на 2&nbsp;мм снимают профильной фрезой. Без фаски торец
                выглядит толстым и цепляет одежду.
              </li>
              <li>
                Лента 0,4&nbsp;мм повторяет неровности пласти. Если торец после
                пилы со сколами, тонкая кромка это не спрячет.
              </li>
            </ul>
          </section>

          <section className="border border-[#d7dde2] bg-white rounded-xl p-6">
            <h2 className="mb-3 text-[20px] font-bold">Кромка в спецификации АвтоРаскроя</h2>
            <p>
              Сервис проставляет толщину кромки по типу панели: фасад получает
              2&nbsp;мм, видимые торцы корпуса 1&nbsp;мм, скрытые 0,4&nbsp;мм.
              Размеры деталей пересчитываются с учётом кромки, а в{' '}
              <Link href="/blog/karta-raskroya-ldsp" className="underline underline-offset-4">
                карту раскроя
              </Link>{' '}
              попадают уже готовые к распилу габариты.
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
