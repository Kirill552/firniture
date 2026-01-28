"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Coins, ChevronDown, ChevronUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";

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

export function CostSummary({ orderId }: { orderId: string }) {
  const [data, setData] = useState<CostEstimate | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    fetch(`/api/v1/orders/${orderId}/cost`)
      .then((res) => {
        if (!res.ok) {
          // 401 или другие ошибки — просто не показываем компонент
          return null;
        }
        return res.json();
      })
      .then((data) => {
        if (data) setData(data);
      })
      .catch(() => {
        // Сетевая ошибка — игнорируем
      })
      .finally(() => setIsLoading(false));
  }, [orderId]);

  if (isLoading) return <Skeleton className="h-48 w-full" />;
  if (!data) return null;

  return (
    <Card className="border-green-500/20 bg-green-50/50 dark:bg-green-900/10">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Coins className="h-5 w-5 text-green-600" />
            Себестоимость изделия
          </CardTitle>
          <Badge variant="secondary" className="text-lg font-bold text-green-700">
            {Math.round(data.total_cost).toLocaleString()} ₽
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-4 mb-4 text-sm">
          <div>
            <p className="text-muted-foreground">Материалы</p>
            <p className="font-semibold">{Math.round(data.materials_cost).toLocaleString()} ₽</p>
          </div>
          <div>
            <p className="text-muted-foreground">Фурнитура</p>
            <p className="font-semibold">{Math.round(data.hardware_cost).toLocaleString()} ₽</p>
          </div>
          <div>
            <p className="text-muted-foreground">Работа</p>
            <p className="font-semibold">{Math.round(data.operations_cost).toLocaleString()} ₽</p>
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
                <span className="font-medium">{Math.round(item.total_price)} ₽</span>
              </div>
            ))}
          </CollapsibleContent>
        </Collapsible>
      </CardContent>
    </Card>
  );
}
