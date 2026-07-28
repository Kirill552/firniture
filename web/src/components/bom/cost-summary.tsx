"use client";

import { useEffect, useState } from "react";
import { getAuthHeader } from "@/lib/auth";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Coins, ChevronDown, ChevronUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { formatMoney } from "@/lib/money";
interface CostBreakdownItem {
  name: string;
  quantity: number;
  unit: string;
  unit_price: number;
  total_price: number;
}

interface CostEstimate {
  total_cost: number;
  currency: string;
  breakdown: CostBreakdownItem[];
  materials_cost: number;
  hardware_cost: number;
  operations_cost: number;
}

interface PurchaseList {
  items: CostBreakdownItem[];
  materials_total: number;
  hardware_total: number;
  services_total: number;
  total: number;
  currency: string;
  prices_are_defaults: boolean;
}

export function CostSummary({ orderId }: { orderId: string }) {
  const [data, setData] = useState<CostEstimate | null>(null);
  const [purchase, setPurchase] = useState<PurchaseList | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    fetch(`/api/v1/orders/${orderId}/cost`, { headers: getAuthHeader() })
      .then((res) => (res.ok ? res.json() : null))
      .then((value) => { if (value) setData(value); })
      .catch(() => undefined)
      .finally(() => setIsLoading(false));
  }, [orderId]);

  useEffect(() => {
    fetch(`/api/v1/orders/${orderId}/purchase-list`, { headers: getAuthHeader() })
      .then((res) => (res.ok ? res.json() : null))
      .then((value) => { if (value) setPurchase(value); })
      .catch(() => undefined);
  }, [orderId]);

  if (isLoading) return <Skeleton className="h-48 w-full" />;
  if (!data) return null;
  return (
    <>
      {purchase && (
        <Card className="mb-4 border-blue-500/20">
          <CardHeader><CardTitle className="text-lg">Что купить</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {purchase.items.map((item, index) => (
              <div key={index} className="flex justify-between text-sm">
                <span>{item.name} — {item.quantity} {item.unit}</span>
                <span className="font-medium">{formatMoney(item.total_price, purchase.currency)}</span>
              </div>
            ))}
            <div className="border-t pt-2 flex justify-between font-bold text-lg">
              <span>Итого</span><span>{formatMoney(purchase.total, purchase.currency)}</span>
            </div>
            {purchase.prices_are_defaults && (
              <p className="text-sm font-medium text-amber-700 dark:text-amber-300">
                Цены прикидочные по российскому рынку. Для валюты {purchase.currency} введите свои цены в <a className="underline" href="/settings">настройках</a>.
              </p>
            )}
          </CardContent>
        </Card>
      )}
      <Card className="border-green-500/20 bg-green-50/50 dark:bg-green-900/10">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Coins className="h-5 w-5 text-green-600" />
            Себестоимость изделия
          </CardTitle>
          <Badge variant="secondary" className="text-lg font-bold text-green-700">
            {formatMoney(data.total_cost, data.currency)}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-4 mb-4 text-sm">
          <div>
            <p className="text-muted-foreground">Материалы</p>
            <p className="font-semibold">{formatMoney(data.materials_cost, data.currency)}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Фурнитура</p>
            <p className="font-semibold">{formatMoney(data.hardware_cost, data.currency)}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Работа</p>
            <p className="font-semibold">{formatMoney(data.operations_cost, data.currency)}</p>
          </div>
        </div>

        <Collapsible open={isOpen} onOpenChange={setIsOpen}>
          <CollapsibleTrigger asChild>
            <Button variant="ghost" size="sm" className="w-full text-muted-foreground">
              {isOpen ? "Скрыть детализацию" : "Показать детализацию"}
              {isOpen ? <ChevronUp className="ml-2 h-4 w-4" /> : <ChevronDown className="ml-2 h-4 w-4" />}
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-4 space-y-2">
            {data.breakdown.map((item, i) => (
              <div key={i} className="flex justify-between text-sm border-b border-border/50 pb-1 last:border-0">
                <span className="text-muted-foreground">
                  {item.name} ({item.quantity} {item.unit})
                </span>
                <span className="font-medium">{formatMoney(item.total_price, data.currency)}</span>
              </div>
            ))}
          </CollapsibleContent>
        </Collapsible>
      </CardContent>
    </Card>
      </>
  );
}
