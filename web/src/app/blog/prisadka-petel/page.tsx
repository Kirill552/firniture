import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Присадка петель: схема разметки под мебельные петли 35 мм — АвтоРаскрой',
  description:
    'Как разметить фасад под чашку петли 35 мм: расстояние от края, система 32 мм, глубина сверления, количество петель по высоте двери. Схемы и таблицы.',
  alternates: { canonical: '/blog/prisadka-petel' },
};

const articleJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'Article',
  headline: 'Присадка петель: схема разметки под мебельные петли 35 мм',
  description:
    'Разметка фасада под чашку петли 35 мм: отступ от края, система 32 мм, глубина, количество петель по высоте двери.',
  author: { '@type': 'Organization', name: 'АвтоРаскрой' },
  publisher: { '@type': 'Organization', name: 'АвтоРаскрой' },
  datePublished: '2026-07-12',
  inLanguage: 'ru',
};

/**
 * Статья «Присадка петель» — кластер ~4300 показов/мес (Wordstat).
 * Практический гайд: размеры из реальных шаблонов присадки (drilling_templates).
 */
export default function PrisadkaPetelPage() {
  return (
    <main className="min-h-screen bg-[#f3f6f8] text-[#171a1d]">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(articleJsonLd) }}
      />
      <div className="mx-auto max-w-[760px] px-6 py-16">
        <nav className="text-[12px] text-[#66707a]">
          <Link href="/" className="hover:text-[#171a1d]">Главная</Link>
          <span className="mx-2">/</span>
          <Link href="/blog" className="hover:text-[#171a1d]">Статьи</Link>
          <span className="mx-2">/</span>
          <span>Присадка петель</span>
        </nav>

        <h1 className="mt-6 text-[32px] md:text-[38px] font-extrabold leading-[1.05] tracking-[-1px]">
          Присадка петель: схема разметки под мебельные петли 35&nbsp;мм
        </h1>
        <p className="mt-3 text-[13px] text-[#66707a]">12 июля 2026 · 6 мин чтения</p>

        <div className="mt-10 space-y-8 text-[15px] leading-relaxed">
          <p>
            Присадка — это сверловка отверстий под фурнитуру: чашки петель,
            направляющие, конфирматы и эксцентрики. Ошибка в паре миллиметров, и
            дверь висит криво или не закрывается. Ниже разметка под самую ходовую
            мебельную петлю с чашкой 35&nbsp;мм (Blum, Hettich, Boyard и аналоги).
          </p>

          <section>
            <h2 className="mb-3 text-[20px] font-bold">Что сверлим под петлю</h2>
            <ul className="list-disc space-y-2 pl-6">
              <li>
                Чашка ø35 мм под корпус петли, сверло Форстнера. Глубина зависит
                от модели: у Blum CLIP top 110° это 13&nbsp;мм, у версий на 107°
                бывает 11,5–12&nbsp;мм. Сверяйтесь с каталогом своей петли.
              </li>
              <li>
                Два отверстия ø4–5 мм под саморезы крепления чашки
                (или ø5 × 12 под еврошуруп/дуодюбель).
              </li>
              <li>
                Отверстия в боковине под монтажную планку: система 32 мм,
                сверло ø5 мм, глубина 12 мм.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="mb-3 text-[20px] font-bold">Ключевой размер: отступ K от края фасада</h2>
            <p>
              K — расстояние от края фасада до края чашки. В каталогах Blum оно
              задано диапазоном 3–7&nbsp;мм: чем больше K, тем меньше дверь
              накрывает боковину. Центр отверстия ø35 считается как K плюс
              радиус чашки 17,5&nbsp;мм, то есть 20,5–24,5&nbsp;мм от края.
              В шаблонах АвтоРаскроя по умолчанию стоит 21,5&nbsp;мм (K = 4).
            </p>
            <div className="mt-4 border border-[#d7dde2] bg-white rounded-xl p-5">
              <div className="font-mono text-[11px] uppercase tracking-[2px] text-[#66707a] mb-3">
                Типовые значения
              </div>
              <table className="w-full text-[14px]">
                <thead>
                  <tr className="text-left text-[#66707a] border-b border-[#d7dde2]">
                    <th className="py-2">Тип петли</th>
                    <th className="py-2">K (край → чашка)</th>
                    <th className="py-2">Центр от края</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b border-[#d7dde2]">
                    <td className="py-2">Накладная</td>
                    <td className="py-2">3–7 мм</td>
                    <td className="py-2">20,5–24,5 мм</td>
                  </tr>
                  <tr className="border-b border-[#d7dde2]">
                    <td className="py-2">Полунакладная</td>
                    <td className="py-2">9–10 мм</td>
                    <td className="py-2">≈ 27 мм</td>
                  </tr>
                  <tr>
                    <td className="py-2">Вкладная (внутренняя)</td>
                    <td className="py-2">14–16 мм</td>
                    <td className="py-2">≈ 32 мм</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section>
            <h2 className="mb-3 text-[20px] font-bold">Сколько петель на дверь</h2>
            <p className="mb-4">
              Blum и Hettich считают количество петель по высоте и весу фасада,
              причём вес важнее: тяжёлый МДФ высотой 900 мм требует больше
              петель, чем лёгкий ЛДСП той же высоты. Таблица ниже — то, что
              подставляет калькулятор сервиса, когда вес неизвестен.
            </p>
            <table className="w-full text-[14px] border border-[#d7dde2] bg-white rounded-xl overflow-hidden">
              <thead>
                <tr className="text-left text-[#66707a] border-b border-[#d7dde2]">
                  <th className="py-2 px-4">Высота фасада</th>
                  <th className="py-2 px-4">Петель</th>
                  <th className="py-2 px-4">Ориентир по весу</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-[#d7dde2]">
                  <td className="py-2 px-4">до 900 мм</td>
                  <td className="py-2 px-4">2</td>
                  <td className="py-2 px-4">до 12 кг</td>
                </tr>
                <tr className="border-b border-[#d7dde2]">
                  <td className="py-2 px-4">900–1200 мм</td>
                  <td className="py-2 px-4">3</td>
                  <td className="py-2 px-4">до 17 кг</td>
                </tr>
                <tr className="border-b border-[#d7dde2]">
                  <td className="py-2 px-4">1200–2000 мм</td>
                  <td className="py-2 px-4">4</td>
                  <td className="py-2 px-4">до 22 кг</td>
                </tr>
                <tr>
                  <td className="py-2 px-4">свыше 2000 мм</td>
                  <td className="py-2 px-4">5</td>
                  <td className="py-2 px-4">от 22 кг</td>
                </tr>
              </tbody>
            </table>
            <p className="mt-3">
              Крайние петли ставят на 70–100 мм от верха и низа фасада: чем
              ближе к краю, тем меньше дверь пружинит. Средние распределяют
              равномерно, расстояние между соседними петлями держат не меньше
              280–300 мм. Фасад шире 600 мм тоже просит дополнительную петлю,
              даже если по высоте хватало двух.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-[20px] font-bold">Монтажная планка: система 32 мм</h2>
            <p>
              Ответная часть крепится к боковине корпуса по системе 32 мм:
              первое отверстие на 32 мм от передней кромки боковины
              (для накладной двери), второе на 64 мм. Высота планки считается
              от центра чашки петли с поправкой на накладку корпуса.
              На присадочном станке это две стандартные позиции; вручную
              размечайте шаблоном, шаг 32 мм не прощает разметки на глаз.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-[20px] font-bold">Частые ошибки</h2>
            <ul className="list-disc space-y-2 pl-6">
              <li>
                Сверление насквозь. При ЛДСП 16 мм и чашке глубиной 13 мм
                ограничитель на сверле обязателен.
              </li>
              <li>
                Одинаковый K для всех петель. У разных производителей посадка
                отличается, сверяйтесь с таблицей конкретной модели.
              </li>
              <li>
                Разметка от кромки без учёта кромления: лента 1–2 мм добавляет
                к габариту фасада.
              </li>
              <li>
                Планка без привязки к 32 мм. Сдвиг на 3 мм, и дверь уже
                не регулируется в нужном диапазоне.
              </li>
            </ul>
          </section>

          <section className="border border-[#d7dde2] bg-white rounded-xl p-6">
            <h2 className="mb-3 text-[20px] font-bold">Как это считает АвтоРаскрой</h2>
            <p>
              Сервис рассчитывает присадку автоматически: по типу изделия и
              высоте двери определяется количество петель, по шаблону
              фурнитуры — позиции чашек, крепежа и монтажных планок в системе
              32 мм. Все точки попадают в DXF отдельными слоями: контур,
              чашка ø35, крепёж ø5. Как считается раскладка панелей на листе —
              в статье{' '}
              <Link href="/blog/karta-raskroya-ldsp" className="underline underline-offset-4">
                «Карта раскроя ЛДСП»
              </Link>
              .
            </p>
            <Link
              href="/new"
              className="mt-4 inline-flex items-center gap-2 rounded-xl bg-[#171a1d] px-6 py-3 text-[14px] font-bold text-white hover:bg-black transition-colors"
            >
              Попробовать на своём эскизе →
            </Link>
          </section>
        </div>
      </div>
    </main>
  );
}
