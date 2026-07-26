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
  datePublished: '2026-07-26',
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
        <p className="mt-3 text-[13px] text-[#66707a]">26 июля 2026 · 6 мин чтения</p>

        <div className="mt-10 space-y-8 text-[15px] leading-relaxed">
          <p>
            «Присадка» — это сверловка отверстий под фурнитуру: чашки петель,
            направляющие, конфирматы и эксцентрики. Ошибка в паре миллиметров —
            и дверь висит криво или не закрывается. Разберём разметку под
            самую ходовую мебельную петлю — с чашкой 35&nbsp;мм (Blum, Boyard,
            Hettich и аналоги).
          </p>

          <section>
            <h2 className="mb-3 text-[20px] font-bold">Что сверлим под петлю</h2>
            <ul className="list-disc space-y-2 pl-6">
              <li>
                <b>Чашка ø35 мм</b>, глубина 12–13 мм — под корпус петли.
                Сверло Форстнера 35 мм.
              </li>
              <li>
                <b>Два отверстия ø4–5 мм</b> под саморезы крепления чашки
                (или ø5 × 12 под еврошуруп/дуодюбель).
              </li>
              <li>
                <b>Отверстия в боковине</b> под монтажную планку: система 32 мм,
                сверло ø5 мм, глубина 12 мм.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="mb-3 text-[20px] font-bold">Ключевой размер: отступ K от края фасада</h2>
            <p>
              Расстояние от края фасада до края чашки (обозначается K)
              определяет накладку двери на корпус. Для стандартной накладной
              петли: <b>K = 3–5 мм</b> — центр чашки на 21–22 мм от края фасада
              (K + радиус чашки 17,5 мм + зазор). Увеличиваете K — дверь
              «уезжает» внутрь корпуса, уменьшаете — больше накладка снаружи.
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
                    <td className="py-2">3–5 мм</td>
                    <td className="py-2">≈ 21–22 мм</td>
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
            <table className="w-full text-[14px] border border-[#d7dde2] bg-white rounded-xl overflow-hidden">
              <thead>
                <tr className="text-left text-[#66707a] border-b border-[#d7dde2]">
                  <th className="py-2 px-4">Высота двери</th>
                  <th className="py-2 px-4">Петель (ЛДСП 16 мм)</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-[#d7dde2]">
                  <td className="py-2 px-4">до 600 мм</td>
                  <td className="py-2 px-4">2</td>
                </tr>
                <tr className="border-b border-[#d7dde2]">
                  <td className="py-2 px-4">600–1000 мм</td>
                  <td className="py-2 px-4">2 (3 при тяжёлом фасаде)</td>
                </tr>
                <tr className="border-b border-[#d7dde2]">
                  <td className="py-2 px-4">1000–1600 мм</td>
                  <td className="py-2 px-4">3</td>
                </tr>
                <tr>
                  <td className="py-2 px-4">свыше 1600 мм</td>
                  <td className="py-2 px-4">4–5</td>
                </tr>
              </tbody>
            </table>
            <p className="mt-3">
              Крайние петли ставят на 70–100 мм от верха и низа фасада —
              чем ближе к краю, тем меньше дверь «пружинит».
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-[20px] font-bold">Монтажная планка: система 32 мм</h2>
            <p>
              Ответная часть крепится к боковине корпуса по системе 32 мм:
              первое отверстие на 32 мм от передней кромки боковины
              (для накладной двери), второе — на 64 мм. Высота планки считается
              от центра чашки петли с поправкой на накладку корпуса.
              На присадочном станке это две стандартные позиции; вручную
              размечайте шаблоном — шаг 32 мм не прощает разметки «на глаз».
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-[20px] font-bold">Частые ошибки</h2>
            <ul className="list-disc space-y-2 pl-6">
              <li>
                <b>Сверление насквозь.</b> Глубина чашки 12–13 мм при ЛДСП 16 мм —
                ограничитель на сверле обязателен.
              </li>
              <li>
                <b>Одинаковый K для всех петель.</b> У разных производителей
                посадка отличается — сверяйтесь с таблицей конкретной петли.
              </li>
              <li>
                <b>Разметка от кромки без учёта кромления.</b> Кромка 1–2 мм
                добавляет к габариту фасада.
              </li>
              <li>
                <b>Планка без привязки к 32 мм.</b> Сдвиг на 3 мм — и дверь
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
              чашка ø35, крепёж ø5.
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
