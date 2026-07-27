import type { Metadata } from 'next';
import Link from 'next/link';
import { LEGAL } from '@/lib/legal';

export const metadata: Metadata = {
  title: 'Политика конфиденциальности',
  description:
    'Политика обработки персональных данных сервиса АвтоРаскрой в соответствии с 152-ФЗ.',
};

/**
 * Политика конфиденциальности (152-ФЗ). Реквизиты — из LEGAL (SSOT).
 */
export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-[#f3f6f8] text-[#171a1d]">
      <div className="mx-auto max-w-[760px] px-6 py-16">
        <Link
          href="/"
          className="text-[13px] font-semibold text-[#66707a] hover:text-[#171a1d]"
        >
          ← На главную
        </Link>

        <h1 className="mt-6 text-[32px] font-extrabold leading-tight tracking-[-1px]">
          Политика конфиденциальности
        </h1>
        <p className="mt-2 text-[13px] text-[#66707a]">
          Редакция от {LEGAL.updatedAt}
        </p>

        <div className="mt-10 space-y-8 text-[15px] leading-relaxed text-[#171a1d]">
          <section>
            <h2 className="mb-3 text-[18px] font-bold">1. Оператор персональных данных</h2>
            <p>
              Оператором персональных данных является {LEGAL.operatorName},{' '}
              {LEGAL.operatorForm} (ИНН {LEGAL.inn}), далее — «Оператор».
              Настоящая политика действует в отношении всех данных, которые
              Оператор получает от пользователей сервиса «{LEGAL.serviceName}»
              ({LEGAL.siteUrl}), в соответствии с Федеральным законом от
              27.07.2006 № 152-ФЗ «О персональных данных».
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-[18px] font-bold">2. Какие данные мы обрабатываем</h2>
            <ul className="list-disc space-y-2 pl-6">
              <li>
                адрес электронной почты — при регистрации и входе по
                magic-ссылке;
              </li>
              <li>
                название фабрики и параметры производства — при настройке
                профиля;
              </li>
              <li>
                загруженные эскизы и параметры заказов — для выполнения
                основной функции сервиса;
              </li>
              <li>
                обезличенные технические события (тип устройства, действия в
                интерфейсе) — только после вашего согласия в баннере
                аналитики, без содержимого эскизов, размеров и почты.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="mb-3 text-[18px] font-bold">3. Цели обработки</h2>
            <p>
              Данные обрабатываются для: предоставления доступа к сервису и
              сохранения заказов; отправки magic-ссылок для входа; улучшения
              качества распознавания и интерфейса (по обезличенным данным и
              только с согласия); выполнения требований законодательства РФ.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-[18px] font-bold">4. Правовые основания и согласие</h2>
            <p>
              Основанием обработки является согласие субъекта персональных
              данных (ст. 6 152-ФЗ), выраженное регистрацией в сервисе и
              принятием оферты, а также исполнение договора. Согласие на сбор
              аналитики запрашивается отдельно и может быть отклонено без
              ограничения функций сервиса.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-[18px] font-bold">5. Хранение и защита</h2>
            <p>
              Данные хранятся на серверах на территории Российской Федерации.
              Доступ к заказам ограничен владельцем учётной записи; гостевые
              эскизы привязаны к подписанной сессии браузера. Передача данных
              третьим лицам не осуществляется, за исключением операторов
              связи (отправка e-mail) и случаев, предусмотренных законом.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-[18px] font-bold">
              5.1. Сервисы веб-аналитики
            </h2>
            <p>
              После согласия в баннере аналитики на страницах подключается
              Яндекс.Метрика (ООО «ЯНДЕКС», серверы на территории России).
              Метрика сохраняет cookie и собирает обезличенные сведения о
              посещении: страницы, источник перехода, тип устройства,
              действия в интерфейсе, запись сессии в Вебвизоре без ввода
              персональных данных. Условия использования Метрики опубликованы
              на{' '}
              <a
                href="https://yandex.ru/legal/metrica_termsofuse/"
                target="_blank"
                rel="noopener noreferrer"
                className="font-semibold underline decoration-[#d7dde2] underline-offset-4"
              >
                yandex.ru/legal/metrica_termsofuse
              </a>
              . Без согласия счётчик не загружается; отозвать согласие можно,
              очистив cookie сайта или отклонив баннер повторно.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-[18px] font-bold">6. Права субъекта данных</h2>
            <p>
              Вы вправе запросить уточнение, блокирование или удаление своих
              персональных данных, а также отозвать согласие на обработку,
              направив запрос на{' '}
              <a
                href={`mailto:${LEGAL.email}`}
                className="font-semibold underline decoration-[#d7dde2] underline-offset-4"
              >
                {LEGAL.email}
              </a>
              . Оператор отвечает на запросы в срок, установленный 152-ФЗ.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-[18px] font-bold">7. Реквизиты Оператора</h2>
            <p>
              {LEGAL.operatorName}
              <br />
              {LEGAL.operatorForm}
              <br />
              ИНН {LEGAL.inn}
              <br />
              E-mail:{' '}
              <a
                href={`mailto:${LEGAL.email}`}
                className="font-semibold underline decoration-[#d7dde2] underline-offset-4"
              >
                {LEGAL.email}
              </a>
            </p>
          </section>
        </div>
      </div>
    </main>
  );
}
