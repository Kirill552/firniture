"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { FileDropzone } from "@/components/vision/file-dropzone";
import { ExtractedParamsCard } from "@/components/vision/extracted-params-card";
import { useVisionOCR } from "@/hooks/use-vision-ocr";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { Keyboard, ArrowLeft } from "lucide-react";

// Маппинг русских названий → enum значения для API
const CABINET_TYPE_MAP: Record<string, string> = {
  // Русские названия
  "навесной": "wall",
  "навесной шкаф": "wall",
  "верхний": "wall",
  "верхний шкаф": "wall",
  "напольный": "base",
  "напольная тумба": "base",
  "нижний": "base",
  "нижний шкаф": "base",
  "тумба": "base",
  "тумба под мойку": "base_sink",
  "мойка": "base_sink",
  "под мойку": "base_sink",
  "с ящиками": "drawer",
  "тумба с ящиками": "drawer",
  "ящики": "drawer",
  "пенал": "tall",
  "шкаф-пенал": "tall",
  "высокий": "tall",
  "угловой": "corner",
  "угловой шкаф": "corner",
  "угол": "corner",
  // Общие
  "шкаф": "base",
  "кухонный": "base",
  "кухонный шкаф": "base",
  // Английские (на случай если уже правильные)
  "wall": "wall",
  "base": "base",
  "base_sink": "base_sink",
  "drawer": "drawer",
  "tall": "tall",
  "corner": "corner",
};

function mapCabinetType(input: string): string {
  const normalized = input.toLowerCase().trim();
  return CABINET_TYPE_MAP[normalized] || "base";
}

export default function NewOrderPage() {
  const router = useRouter();
  const { toast } = useToast();
  const { analyze, isLoading, result } = useVisionOCR();
  const [isCreating, setIsCreating] = useState(false);

  const handleFileSelect = async (file: File) => {
    const ocrResult = await analyze(file);

    if (!ocrResult?.success) {
      toast({
        title: "Ошибка распознавания",
        description: "Попробуйте другое фото или введите данные вручную",
        variant: "destructive",
      });
    }
  };

  const handleConfirm = async (params: Record<string, unknown>) => {
    setIsCreating(true);

    try {
      // Извлечь и нормализовать параметры
      const rawProductType = (params.product_type || params.cabinet_type || "base") as string;
      const cabinetType = mapCabinetType(rawProductType);
      const width_mm = Number(params.width_mm || params.width) || 600;
      const height_mm = Number(params.height_mm || params.height) || 720;
      const depth_mm = Number(params.depth_mm || params.depth) || 560;
      const material = (params.material || "ЛДСП") as string;
      const thickness = Number(params.thickness || params.thickness_mm) || 16;

      // Создать заказ
      const orderResponse = await fetch("/api/v1/orders/anonymous", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: rawProductType,
          description: "Создан через Vision OCR",
          spec: { ...params, product_type: cabinetType, width: width_mm, height: height_mm, depth: depth_mm },
        }),
      });

      if (!orderResponse.ok) {
        throw new Error("Ошибка создания заказа");
      }

      const order = await orderResponse.json();

      // Маппинг для BOM generate endpoint
      const bomParams = {
        order_id: order.id,
        cabinet_type: cabinetType,
        width_mm,
        height_mm,
        depth_mm,
        material: `${material} ${thickness}мм`,
        shelf_count: cabinetType === "tall" ? 4 : 1,
        door_count: cabinetType === "drawer" ? 0 : (width_mm > 600 ? 2 : 1),
        drawer_count: cabinetType === "drawer" ? 3 : 0,
      };

      // Сгенерировать BOM
      const bomResponse = await fetch("/api/v1/bom/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(bomParams),
      });

      if (!bomResponse.ok) {
        console.error("BOM generation failed:", await bomResponse.text());
      }

      // Перейти в BOM (минуя диалог!)
      router.push(`/bom?orderId=${order.id}`);
    } catch (error) {
      toast({
        title: "Ошибка",
        description: "Не удалось создать заказ",
        variant: "destructive",
      });
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/20">
      <div className="container mx-auto max-w-2xl px-4 py-12">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold tracking-tight">
            Сфоткай эскиз — получи файлы за 30 секунд
          </h1>
          <p className="mt-2 text-muted-foreground">
            Загрузите фото, и мы автоматически распознаем размеры и материалы
          </p>
        </div>

        {/* Зона загрузки */}
        {!result?.success && (
          <FileDropzone onFileSelect={handleFileSelect} isLoading={isLoading} />
        )}

        {/* Результат распознавания */}
        {result?.success && result.parameters && (
          <ExtractedParamsCard
            params={result.parameters}
            confidence={result.ocr_confidence}
            onConfirm={handleConfirm}
            isLoading={isCreating}
          />
        )}

        {/* Альтернативы */}
        <div className="mt-8 flex flex-col items-center gap-4">
          <div className="flex items-center gap-4">
            <div className="h-px flex-1 bg-border" />
            <span className="text-sm text-muted-foreground">или</span>
            <div className="h-px flex-1 bg-border" />
          </div>

          <div className="flex gap-4">
            <Link href="/new/manual">
              <Button variant="outline">
                <Keyboard className="mr-2 h-4 w-4" />
                Ввести вручную
              </Button>
            </Link>
          </div>
        </div>

        {/* Назад */}
        <div className="mt-12 text-center">
          <Link href="/">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="mr-2 h-4 w-4" />
              На главную
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
