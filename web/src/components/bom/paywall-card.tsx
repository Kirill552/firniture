"use client";

import { useCallback } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CheckCircle2, Download, Gift, Loader2 } from "lucide-react";
import { useOrderAccess } from "@/hooks/use-order-access";
import {
  ORDER_PRICE_RUB,
  PACK_PRICE_RUB,
  PACK_SIZE,
  isPaymentRequiredError,
} from "@/lib/payments";
import { OrderExportButtons } from "./order-export-buttons";
import { OrderPaymentBlock } from "./order-payment-block";

interface PaywallCardProps {
  orderId: string;
  dxfDownloadUrl?: string | null;
  pdfDownloadUrl?: string | null;
  onGenerateDxf?: () => Promise<void>;
  onGeneratePdf?: () => Promise<void>;
  isGeneratingDxf?: boolean;
  isGeneratingPdf?: boolean;
  /** Пользователь вернулся с платёжной страницы ЮKassa — ждём вебхук. */
  returnedFromPayment?: boolean;
}

const ACCESS_REASON_TEXT: Record<string, string> = {
  free_first: "Первый заказ фабрики — бесплатно",
  payment: "Заказ оплачен. Повторные скачивания этой ревизии бесплатны",
  pack: "Списан один заказ из пакета. Повторные скачивания бесплатны",
};

/**
 * Пейволл заказа: единица оплаты — заказ целиком, сколько бы изделий в нём ни было.
 * Доступ определяет бэкенд, фронт только показывает состояние и ведёт на ЮKassa.
 */
export function PaywallCard({
  orderId,
  dxfDownloadUrl,
  pdfDownloadUrl,
  onGenerateDxf,
  onGeneratePdf,
  isGeneratingDxf = false,
  isGeneratingPdf = false,
  returnedFromPayment = false,
}: PaywallCardProps) {
  const {
    access,
    balance,
    isLoading,
    loadError,
    isWaitingPayment,
    waitTimedOut,
    checkoutKind,
    checkoutError,
    buy,
    reload,
    markPaymentRequired,
  } = useOrderAccess(orderId, returnedFromPayment);

  // Экспорт списывает бесплатный заказ или кредит пакета, поэтому доступ
  // перечитываем. Ответ 402 означает, что платить всё-таки нужно.
  const runExport = useCallback(
    async (generate?: () => Promise<void>) => {
      if (!generate) return;
      try {
        await generate();
        reload();
      } catch (error) {
        if (isPaymentRequiredError(error)) markPaymentRequired(error);
      }
    },
    [markPaymentRequired, reload]
  );

  const openDxf = () => {
    if (dxfDownloadUrl) {
      window.open(dxfDownloadUrl, "_blank");
      return;
    }
    void runExport(onGenerateDxf);
  };

  const openPdf = () => {
    if (pdfDownloadUrl) {
      window.open(pdfDownloadUrl, "_blank");
      return;
    }
    void runExport(onGeneratePdf);
  };

  if (isWaitingPayment) {
    return (
      <Card className="border-primary/30">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Loader2 className="h-5 w-5 animate-spin" />
            Подтверждаем оплату
          </CardTitle>
          <CardDescription>
            ЮKassa сообщает об оплате в течение нескольких секунд. Не закрывайте страницу —
            доступ к файлам откроется сам.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Loader2 className="h-5 w-5 animate-spin" />
            Проверяем доступ к заказу
          </CardTitle>
        </CardHeader>
      </Card>
    );
  }

  if (access?.access) {
    return (
      <Card className="border-green-500 bg-green-50/50 dark:bg-green-900/10">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-green-700">
            <CheckCircle2 className="h-6 w-6" />
            Файлы для производства доступны
          </CardTitle>
          <CardDescription>
            {ACCESS_REASON_TEXT[access.reason ?? ""] ?? "Доступ к файлам этого заказа открыт"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <OrderExportButtons
            dxfDownloadUrl={dxfDownloadUrl}
            pdfDownloadUrl={pdfDownloadUrl}
            isGeneratingDxf={isGeneratingDxf}
            isGeneratingPdf={isGeneratingPdf}
            onDxf={openDxf}
            onPdf={openPdf}
          />
        </CardContent>
      </Card>
    );
  }

  const packCredits = access?.pack_credits ?? 0;
  const freeFirst = access?.free_first_available === true;

  if (access && (freeFirst || packCredits > 0)) {
    return (
      <Card className="border-primary/30">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Gift className="h-5 w-5" />
            {freeFirst ? "Первый заказ — бесплатно" : `В пакете осталось ${packCredits} заказов`}
          </CardTitle>
          <CardDescription>
            {freeFirst
              ? "Заберите файлы всего заказа: платить за первый заказ фабрики не нужно."
              : "При скачивании спишем один заказ из пакета. Повторные скачивания бесплатны."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button size="lg" className="w-full" onClick={openDxf} disabled={isGeneratingDxf}>
            {isGeneratingDxf ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Download className="mr-2 h-4 w-4" />
            )}
            {freeFirst ? "Скачать первый заказ бесплатно" : "Скачать — спишем 1 заказ из пакета"}
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <OrderPaymentBlock
      priceRub={access?.price_rub ?? balance?.price_rub ?? ORDER_PRICE_RUB}
      packPriceRub={balance?.pack_price_rub ?? PACK_PRICE_RUB}
      packSize={balance?.pack_size ?? PACK_SIZE}
      packCredits={packCredits}
      checkoutKind={checkoutKind}
      checkoutError={checkoutError ?? loadError}
      paymentTimedOut={waitTimedOut}
      onBuy={buy}
    />
  );
}
