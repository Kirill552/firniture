"use client";

import { Button } from "@/components/ui/button";
import { FileCode, FileDigit, Loader2 } from "lucide-react";

interface OrderExportButtonsProps {
  dxfDownloadUrl?: string | null;
  pdfDownloadUrl?: string | null;
  isGeneratingDxf: boolean;
  isGeneratingPdf: boolean;
  onDxf: () => void;
  onPdf: () => void;
}

/** Кнопки выгрузки оплаченного заказа: DXF раскроя и PDF карты раскроя. */
export function OrderExportButtons({
  dxfDownloadUrl,
  pdfDownloadUrl,
  isGeneratingDxf,
  isGeneratingPdf,
  onDxf,
  onPdf,
}: OrderExportButtonsProps) {
  return (
    <div className="grid gap-3">
      <Button className="w-full" variant="outline" onClick={onDxf} disabled={isGeneratingDxf}>
        {isGeneratingDxf ? (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        ) : (
          <FileCode className="mr-2 h-4 w-4" />
        )}
        {isGeneratingDxf ? "Генерация…" : dxfDownloadUrl ? "Скачать DXF" : "Создать DXF"}
      </Button>
      <Button className="w-full" variant="outline" onClick={onPdf} disabled={isGeneratingPdf}>
        {isGeneratingPdf ? (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        ) : (
          <FileDigit className="mr-2 h-4 w-4" />
        )}
        {isGeneratingPdf ? "Генерация…" : pdfDownloadUrl ? "Скачать PDF карту" : "Создать PDF карту раскроя"}
      </Button>
    </div>
  );
}
