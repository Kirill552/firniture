import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'DXF для ЧПУ: версия формата, слои и подготовка файла — АвтоРаскрой',
  description:
    'Какой DXF понимает станок: версия R12 или R2013, слои под контур и присадку, единицы, замкнутые контуры вместо сплайнов. И где в цепочке появляется G-code.',
  alternates: { canonical: '/blog/dxf-dlya-chpu' },
  openGraph: {
    type: 'article',
    locale: 'ru_RU',
    url: '/blog/dxf-dlya-chpu',
    siteName: 'АвтоРаскрой',
    title: 'DXF для ЧПУ: версия формата, слои и подготовка файла — АвтоРаскрой',
    description: 'Какой DXF понимает станок: версия R12 или R2013, слои под контур и присадку, единицы, замкнутые контуры вместо сплайнов. И где в цепочке появляется G-code.',
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
  headline: 'DXF для ЧПУ: версия формата, слои и подготовка файла',
  description:
    'Подготовка DXF для мебельного ЧПУ: версии формата, слои, единицы измерения, полилинии, переход в G-code через CAM.',
  author: { '@type': 'Organization', name: 'АвтоРаскрой' },
  publisher: { '@type': 'Organization', name: 'АвтоРаскрой' },
  datePublished: '2026-07-26',
  inLanguage: 'ru',
};

const faqJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: [
    {
      '@type': 'Question',
      name: 'Какую версию DXF выбрать для ЧПУ?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'Если CAM или стойка отказывается читать файл, сохраняйте в R12 (AC1009) — там только базовые примитивы, и его понимают почти все системы. Современные CAM спокойно читают R2010–R2013, где доступны расширенные данные и слои.',
      },
    },
    {
      '@type': 'Question',
      name: 'Можно ли отдать DXF напрямую станку?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'Обычно нет. DXF — это геометрия, а станок исполняет G-code по ISO 6983. Между ними стоит CAM-система, которая назначает инструмент, глубины и подачи. Часть стоек умеет импортировать DXF, но конвертацию всё равно делает внутри.',
      },
    },
    {
      '@type': 'Question',
      name: 'Почему станок режет не по размеру?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'Чаще всего дело в единицах: файл сохранён в дюймах или без указания $INSUNITS, и CAM трактует числа по-своему. Второй частый случай — незамкнутый контур, из-за которого не считается компенсация радиуса фрезы.',
      },
    },
  ],
};

/**
 * Статья «DXF для ЧПУ» — кластер ~340 показов/мес (Wordstat: «dxf для чпу» 341).
 * Технические детали соответствуют экспорту сервиса: api/dxf_generator.py (R2010, слои
 * CONTOUR/EDGE/DRILLING, $INSUNITS=MM) и api/gcode_generator.py (профили станков, циклы G81/G83).
 */
export default function DxfDlyaChpuPage() {
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
          <span>DXF для ЧПУ</span>
        </nav>

        <h1 className="mt-6 text-[32px] md:text-[38px] font-extrabold leading-[1.05] tracking-[-1px]">
          DXF для ЧПУ: версия формата, слои и подготовка файла
        </h1>
        <p className="mt-3 text-[13px] text-[#66707a]">26 июля 2026 · 6 мин чтения</p>

        <div className="mt-10 space-y-8 text-[15px] leading-relaxed">
          <p>
            DXF — обменный формат чертежей от Autodesk. Внутри лежит геометрия:
            отрезки, дуги, окружности, полилинии, разложенные по слоям. Команд
            для станка там нет. Их создаёт CAM-система, когда превращает контуры
            в траектории и выдаёт G-code по стандарту ISO 6983. Мебельный
            технолог отвечает за первый шаг: чтобы файл открылся и в нём было
            понятно, где контур детали, а где отверстие под петлю.
          </p>

          <section>
            <h2 className="mb-3 text-[20px] font-bold">Версия формата</h2>
            <p>
              R12 (маркер AC1009) поддерживает только простые примитивы. Именно
              поэтому он до сих пор работает как аварийный вариант: если старая
              стойка или бюджетная CAM спотыкается на файле, пересохранение
              в R12 обычно решает вопрос. Версии R2010 и R2013 (AC1024, AC1027)
              несут расширенные данные, включая метаданные к слоям, и подходят
              для современных пакетов.
            </p>
            <p>
              Экспорт АвтоРаскроя сделан на R2010 для панелей и на R2013 для
              заданий с метаданными ревизии в XDATA. Если ваш парк станков
              старше, скажите об этом — нужен профиль под R12.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-[20px] font-bold">Слои: контур, кромка, присадка</h2>
            <p>
              Без слоёв CAM не отличит внешний рез от отверстия. Минимальный
              набор для мебели выглядит так:
            </p>
            <table className="mt-4 w-full text-[14px] border border-[#d7dde2] bg-white rounded-xl overflow-hidden">
              <thead>
                <tr className="text-left text-[#66707a] border-b border-[#d7dde2]">
                  <th className="py-2 px-4">Слой</th>
                  <th className="py-2 px-4">Что в нём</th>
                  <th className="py-2 px-4">Операция</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-[#d7dde2]">
                  <td className="py-2 px-4">CONTOUR</td>
                  <td className="py-2 px-4">Замкнутый контур детали</td>
                  <td className="py-2 px-4">Обрезка фрезой насквозь</td>
                </tr>
                <tr className="border-b border-[#d7dde2]">
                  <td className="py-2 px-4">DRILLING</td>
                  <td className="py-2 px-4">Окружности отверстий с диаметром</td>
                  <td className="py-2 px-4">Сверление циклами G81 и G83</td>
                </tr>
                <tr className="border-b border-[#d7dde2]">
                  <td className="py-2 px-4">DRILL_V_35, DRILL_V_5, DRILL_H_4</td>
                  <td className="py-2 px-4">Отверстия по диаметрам: чашка, крепёж, направляющие</td>
                  <td className="py-2 px-4">Разные свёрла без ручной сортировки</td>
                </tr>
                <tr className="border-b border-[#d7dde2]">
                  <td className="py-2 px-4">EDGE</td>
                  <td className="py-2 px-4">Стороны под кромку</td>
                  <td className="py-2 px-4">Не режется, идёт на кромкооблицовочный</td>
                </tr>
                <tr>
                  <td className="py-2 px-4">TEXT, SHEET</td>
                  <td className="py-2 px-4">Подписи деталей и граница листа</td>
                  <td className="py-2 px-4">Не обрабатывается, нужно оператору</td>
                </tr>
              </tbody>
            </table>
            <p className="mt-3">
              Диаметр отверстия задаётся геометрией окружности, а не текстом
              рядом. Чашка петли выходит окружностью ø35, крепёж ø5, отверстия
              полкодержателей ø5 с шагом 32&nbsp;мм.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-[20px] font-bold">Единицы и ноль детали</h2>
            <p>
              В заголовке файла живёт переменная $INSUNITS. Когда она не
              заполнена, CAM выбирает единицы сама, и деталь 600&nbsp;мм может
              приехать размером 600 дюймов. Правильно: миллиметры, начало
              координат в левом нижнем углу детали, ось Y вверх. Тогда ноль
              заготовки на станке совпадает с нулём чертежа без пересчётов.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-[20px] font-bold">Геометрия, которую любит CAM</h2>
            <ul className="list-disc space-y-2 pl-6">
              <li>
                Замкнутые контуры полилинией. Разрыв в 0,01&nbsp;мм ломает
                расчёт компенсации радиуса: CAM не понимает, где внутренняя
                сторона реза.
              </li>
              <li>
                Дуги вместо сплайнов. Сплайн разбивается на тысячи отрезков,
                станок дёргается на подаче и оставляет следы на кромке.
              </li>
              <li>
                Никаких дублей. Две линии одна поверх другой дают два прохода
                фрезы по одному месту.
              </li>
              <li>
                Чистый файл: без пустых слоёв, блоков и рамок чертежа. Их
                удаляют командами PURGE и AUDIT перед сохранением.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="mb-3 text-[20px] font-bold">От DXF к G-code</h2>
            <p>
              Дальше цепочка одинаковая: CAM читает слои, назначает инструмент
              и стратегию, постпроцессор переводит траектории в диалект
              конкретной стойки. Weihong NCStudio, Syntec, FANUC и DSP
              отличаются шапкой программы, кодами циклов и единицами паузы,
              поэтому один и тот же контур на разных станках даёт разные файлы.
            </p>
            <p>
              АвтоРаскрой генерирует G-code сразу под выбранный профиль.
              У Weihong подача на резке 600&nbsp;мм/мин, у Syntec и FANUC 800,
              у бюджетных DSP-стоек 500, у Homag 1200. Врезание идёт вдвое
              медленнее резки, сверление 250–400&nbsp;мм/мин. Шпиндель
              18&nbsp;000 об/мин на большинстве профилей, у Homag 24&nbsp;000.
              Глубокие отверстия выполняются циклом G83 с выводом стружки,
              обычные G81.
            </p>
          </section>

          <section className="border border-[#d7dde2] bg-white rounded-xl p-6">
            <h2 className="mb-3 text-[20px] font-bold">Получить DXF из эскиза</h2>
            <p>
              Загрузите фото или PDF наброска: сервис соберёт{' '}
              <Link href="/blog/specifikaciya-mebeli" className="underline underline-offset-4">
                спецификацию
              </Link>
              , рассчитает{' '}
              <Link href="/blog/prisadka-petel" className="underline underline-offset-4">
                присадку под петли
              </Link>{' '}
              и выдаст DXF с разложенными по слоям контурами и отверстиями.
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
