"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FileCode, FileDigit, Download, CheckCircle2, Lock, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface PaywallCardProps {
  orderId: string;
  dxfDownloadUrl?: string | null;
  pdfDownloadUrl?: string | null;
  onGenerateDxf?: () => Promise<void>;
  onGeneratePdf?: () => Promise<void>;
  isGeneratingDxf?: boolean;
  isGeneratingPdf?: boolean;
}

export function PaywallCard({
  orderId,
  dxfDownloadUrl,
  pdfDownloadUrl,
  onGenerateDxf,
  onGeneratePdf,
  isGeneratingDxf = false,
  isGeneratingPdf = false,
}: PaywallCardProps) {
  // В MVP просто заглушка, которая имитирует оплату
  // В реальности здесь была бы интеграция с ЮKassa
  const [isPaid, setIsPaid] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  const handlePayment = async () => {
    setIsProcessing(true);

    // Имитация задержки оплаты
    await new Promise(resolve => setTimeout(resolve, 1500));
    setIsPaid(true);
    setIsProcessing(false);

    // После оплаты генерируем файлы если есть callbacks
    if (onGenerateDxf && !dxfDownloadUrl) {
      await onGenerateDxf();
    }
    // PDF карта раскроя временно отключена (пакетный раскрой — скоро)
    // if (onGeneratePdf && !pdfDownloadUrl) {
    //   await onGeneratePdf();
    // }
  };

  const handleDownloadDxf = () => {
    if (dxfDownloadUrl) {
      window.open(dxfDownloadUrl, '_blank');
    } else if (onGenerateDxf) {
      onGenerateDxf();
    }
  };

  const handleDownloadPdf = () => {
    if (pdfDownloadUrl) {
      window.open(pdfDownloadUrl, '_blank');
    } else if (onGeneratePdf) {
      onGeneratePdf();
    }
  };

  if (isPaid) {
    return (
      <Card className="border-green-500 bg-green-50/50 dark:bg-green-900/10">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-green-700">
            <CheckCircle2 className="h-6 w-6" />
            Оплачено! Файлы доступны
          </CardTitle>
          <CardDescription>
            Вы можете скачать файлы для производства прямо сейчас
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          <Button
            className="w-full"
            variant="outline"
            onClick={handleDownloadDxf}
            disabled={isGeneratingDxf}
          >
            {isGeneratingDxf ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <FileCode className="mr-2 h-4 w-4" />
            )}
            {isGeneratingDxf ? "Генерация..." : dxfDownloadUrl ? "Скачать DXF" : "Создать DXF"}
          </Button>
          {/* PDF карта раскроя временно отключена (пакетный раскрой — скоро)
          <Button
            className="w-full"
            variant="outline"
            onClick={handleDownloadPdf}
            disabled={isGeneratingPdf}
          >
            {isGeneratingPdf ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <FileDigit className="mr-2 h-4 w-4" />
            )}
            {isGeneratingPdf ? "Генерация..." : pdfDownloadUrl ? "Скачать PDF карту" : "Создать PDF"}
          </Button>
          */}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-primary/20 shadow-lg relative overflow-hidden">
      <div className="absolute top-0 right-0 p-4 opacity-10">
        <Lock className="h-24 w-24" />
      </div>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-xl">Файлы для производства</CardTitle>
          <Badge>PRO</Badge>
        </div>
        <CardDescription>
          Получите готовые файлы для раскроя и сверления вашего станка
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm">
            <CheckCircle2 className="h-4 w-4 text-green-500" />
            <span>DXF файлы для раскроя (совместимы с Базис/AutoCAD)</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <CheckCircle2 className="h-4 w-4 text-green-500" />
            <span>Координаты присадки в DXF</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <CheckCircle2 className="h-4 w-4 text-green-500" />
            <span>Список фурнитуры и крепежа</span>
          </div>
        </div>

        <div className="rounded-lg bg-muted p-4 flex items-center justify-between">
          <div>
            <p className="font-bold text-lg">190 ₽</p>
            <p className="text-xs text-muted-foreground">за этот заказ</p>
          </div>
          <div className="text-right">
            <p className="font-bold text-lg text-muted-foreground line-through">390 ₽</p>
            <Badge variant="destructive" className="ml-2">-50%</Badge>
          </div>
        </div>
      </CardContent>
      <CardFooter>
        <Button size="lg" className="w-full" onClick={handlePayment} disabled={isProcessing}>
          {isProcessing ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Обработка...
            </>
          ) : (
            "Оплатить и скачать"
          )}
        </Button>
      </CardFooter>
    </Card>
  );
}
