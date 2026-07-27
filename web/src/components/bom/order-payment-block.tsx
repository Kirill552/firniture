"use client";

import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, Loader2, Lock } from "lucide-react";
import { LEGAL } from "@/lib/legal";
import type { PurchaseKind } from "@/lib/payments";

interface OrderPaymentBlockProps {
  priceRub: number;
  packPriceRub: number;
  packSize: number;
  packCredits: number;
  checkoutKind: PurchaseKind | null;
  checkoutError: string | null;
  /** Вернулись с оплаты, но вебхук так и не пришёл за 30 секунд. */
  paymentTimedOut: boolean;
  onBuy: (kind: PurchaseKind) => void;
}

const INCLUDED = [
  "DXF раскроя всех изделий заказа (Базис, AutoCAD)",
  "PDF карта раскроя листов",
  "Координаты присадки и список фурнитуры",
];

/** Блок оплаты заказа: разовая покупка или пакет. Единица оплаты — заказ целиком. */
export function OrderPaymentBlock({
  priceRub,
  packPriceRub,
  packSize,
  packCredits,
  checkoutKind,
  checkoutError,
  paymentTimedOut,
  onBuy,
}: OrderPaymentBlockProps) {
  const isBusy = checkoutKind !== null;

  return (
    <Card className="border-primary/20 shadow-lg relative overflow-hidden">
      <div className="absolute top-0 right-0 p-4 opacity-10">
        <Lock className="h-24 w-24" />
      </div>
      <CardHeader>
        <CardTitle className="text-xl">Файлы для производства</CardTitle>
        <CardDescription>
          Оплата за заказ целиком — сколько бы изделий в нём ни было. Повторные скачивания
          этой же ревизии бесплатны.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          {INCLUDED.map((item) => (
            <div key={item} className="flex items-center gap-2 text-sm">
              <CheckCircle2 className="h-4 w-4 shrink-0 text-green-500" />
              <span>{item}</span>
            </div>
          ))}
        </div>

        {paymentTimedOut && (
          <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-900/20 dark:text-amber-200">
            Оплата не подтвердилась за 30 секунд. Если деньги списаны — обновите страницу
            через минуту, доступ откроется автоматически. Если этого не произошло, напишите
            на <a className="underline" href={`mailto:${LEGAL.email}`}>{LEGAL.email}</a> и
            укажите номер заказа — откроем доступ вручную или вернём деньги.
          </p>
        )}

        {packCredits > 0 && (
          <Badge variant="secondary">Остаток пакета: {packCredits} заказов</Badge>
        )}

        <div className="rounded-lg bg-muted p-4">
          <p className="text-2xl font-bold">{priceRub.toLocaleString("ru-RU")} ₽</p>
          <p className="text-xs text-muted-foreground">за этот заказ, разово</p>
        </div>

        {checkoutError && <p className="text-sm text-red-600">{checkoutError}</p>}
      </CardContent>
      <CardFooter className="flex-col items-stretch gap-3">
        <Button size="lg" className="w-full" onClick={() => onBuy("order")} disabled={isBusy}>
          {checkoutKind === "order" && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Оплатить {priceRub.toLocaleString("ru-RU")} ₽
        </Button>
        <Button variant="link" className="h-auto p-0 text-sm" onClick={() => onBuy("pack")} disabled={isBusy}>
          {checkoutKind === "pack" && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Пакет {packSize} заказов — {packPriceRub.toLocaleString("ru-RU")} ₽, не сгорает
        </Button>
      </CardFooter>
    </Card>
  );
}
