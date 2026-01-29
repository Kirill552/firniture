"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { FileDropzone } from "@/components/vision/file-dropzone";
import { ExtractedParamsCard } from "@/components/vision/extracted-params-card";
import { useVisionOCR } from "@/hooks/use-vision-ocr";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import { Camera, Keyboard, ArrowLeft, Check, Loader2, MessageSquare } from "lucide-react";

// Маппинг русских названий → enum значения для API
const CABINET_TYPE_MAP: Record<string, string> = {
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
  "шкаф": "base",
  "кухонный": "base",
  "кухонный шкаф": "base",
  "wall": "wall",
  "base": "base",
  "base_sink": "base_sink",
  "drawer": "drawer",
  "tall": "tall",
  "corner": "corner",
};

const PRODUCT_TYPES: Record<string, string> = {
  wall: "Навесной шкаф",
  base: "Напольная тумба",
  base_sink: "Тумба под мойку",
  drawer: "Тумба с ящиками",
  tall: "Пенал",
};

function mapCabinetType(input: string): string {
  const normalized = input.toLowerCase().trim();
  return CABINET_TYPE_MAP[normalized] || "base";
}

type TabId = "photo" | "manual";

export default function NewOrderPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { toast } = useToast();
  const { analyze, isLoading, result } = useVisionOCR();
  const [isCreating, setIsCreating] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Дефолтный таб: photo для новых, manual для авторизованных (упрощённо — всегда photo)
  const tabFromUrl = searchParams.get("tab") as TabId | null;
  const [activeTab, setActiveTab] = useState<TabId>(tabFromUrl || "photo");

  // Синхронизация URL с табом
  useEffect(() => {
    if (tabFromUrl && tabFromUrl !== activeTab) {
      setActiveTab(tabFromUrl);
    }
  }, [tabFromUrl, activeTab]);

  const handleTabChange = (tab: string) => {
    setActiveTab(tab as TabId);
    // Обновить URL без перезагрузки
    const url = new URL(window.location.href);
    url.searchParams.set("tab", tab);
    window.history.replaceState({}, "", url.toString());
  };

  // === Photo tab logic ===
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
      const rawProductType = (params.product_type || params.cabinet_type || "base") as string;
      const cabinetType = mapCabinetType(rawProductType);
      const width_mm = Number(params.width_mm || params.width) || 600;
      const height_mm = Number(params.height_mm || params.height) || 720;
      const depth_mm = Number(params.depth_mm || params.depth) || 560;
      const material = (params.material || "ЛДСП") as string;
      const thickness = Number(params.thickness || params.thickness_mm) || 16;

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

      const bomResponse = await fetch("/api/v1/bom/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(bomParams),
      });

      if (!bomResponse.ok) {
        console.error("BOM generation failed:", await bomResponse.text());
      }

      router.push(`/bom?orderId=${order.id}`);
    } catch {
      toast({
        title: "Ошибка",
        description: "Не удалось создать заказ",
        variant: "destructive",
      });
    } finally {
      setIsCreating(false);
    }
  };

  // === Manual tab logic ===
  const [formData, setFormData] = useState({
    product_type: "",
    width: "",
    height: "",
    depth: "",
    material: "ЛДСП",
    thickness: "16",
  });

  const updateField = (key: string, value: string) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
  };

  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      const width_mm = parseInt(formData.width);
      const height_mm = parseInt(formData.height);
      const depth_mm = parseInt(formData.depth);

      const specParams = {
        product_type: formData.product_type,
        width: width_mm,
        height: height_mm,
        depth: depth_mm,
        material: formData.material,
        thickness: parseInt(formData.thickness),
      };

      const orderResponse = await fetch("/api/v1/orders/anonymous", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: PRODUCT_TYPES[formData.product_type] || "Новый заказ",
          description: "Создан вручную",
          spec: specParams,
        }),
      });

      if (!orderResponse.ok) {
        throw new Error("Ошибка создания заказа");
      }

      const order = await orderResponse.json();

      const bomParams = {
        order_id: order.id,
        cabinet_type: formData.product_type,
        width_mm,
        height_mm,
        depth_mm,
        material: `${formData.material} ${formData.thickness}мм`,
        shelf_count: formData.product_type === "tall" ? 4 : 1,
        door_count: formData.product_type === "drawer" ? 0 : (width_mm > 600 ? 2 : 1),
        drawer_count: formData.product_type === "drawer" ? 3 : 0,
      };

      const bomResponse = await fetch("/api/v1/bom/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(bomParams),
      });

      if (!bomResponse.ok) {
        console.error("BOM generation failed:", await bomResponse.text());
      }

      router.push(`/bom?orderId=${order.id}`);
    } catch {
      toast({
        title: "Ошибка",
        description: "Не удалось создать заказ",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/20">
      <div className="container mx-auto max-w-2xl px-4 py-12">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold tracking-tight">Создать заказ</h1>
          <p className="mt-2 text-muted-foreground">
            Загрузите фото эскиза или введите параметры вручную
          </p>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
          <TabsList className="grid w-full grid-cols-2 mb-6">
            <TabsTrigger value="photo" className="flex items-center gap-2">
              <Camera className="h-4 w-4" />
              Загрузить фото
            </TabsTrigger>
            <TabsTrigger value="manual" className="flex items-center gap-2">
              <Keyboard className="h-4 w-4" />
              Ввести вручную
            </TabsTrigger>
          </TabsList>

          {/* Photo Tab */}
          <TabsContent value="photo" className="mt-0">
            {!result?.success && (
              <FileDropzone onFileSelect={handleFileSelect} isLoading={isLoading} />
            )}

            {result?.success && result.parameters && (
              <ExtractedParamsCard
                params={result.parameters}
                confidence={result.ocr_confidence}
                onConfirm={handleConfirm}
                isLoading={isCreating}
              />
            )}
          </TabsContent>

          {/* Manual Tab */}
          <TabsContent value="manual" className="mt-0">
            <Card>
              <CardHeader>
                <CardTitle>Параметры изделия</CardTitle>
                <CardDescription>
                  Введите размеры и материалы, и мы рассчитаем деталировку
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleManualSubmit} className="space-y-6">
                  <div className="space-y-2">
                    <Label>Тип изделия</Label>
                    <Select
                      value={formData.product_type}
                      onValueChange={(v) => updateField("product_type", v)}
                      required
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Выберите тип" />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(PRODUCT_TYPES).map(([key, label]) => (
                          <SelectItem key={key} value={key}>
                            {label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label>Ширина, мм</Label>
                      <Input
                        type="number"
                        value={formData.width}
                        onChange={(e) => updateField("width", e.target.value)}
                        required
                        min="100"
                        max="3000"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Высота, мм</Label>
                      <Input
                        type="number"
                        value={formData.height}
                        onChange={(e) => updateField("height", e.target.value)}
                        required
                        min="100"
                        max="3000"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Глубина, мм</Label>
                      <Input
                        type="number"
                        value={formData.depth}
                        onChange={(e) => updateField("depth", e.target.value)}
                        required
                        min="100"
                        max="1200"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Материал корпуса</Label>
                      <Select
                        value={formData.material}
                        onValueChange={(v) => updateField("material", v)}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="ЛДСП">ЛДСП</SelectItem>
                          <SelectItem value="МДФ">МДФ</SelectItem>
                          <SelectItem value="Фанера">Фанера</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>Толщина, мм</Label>
                      <Select
                        value={formData.thickness}
                        onValueChange={(v) => updateField("thickness", v)}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="16">16 мм</SelectItem>
                          <SelectItem value="18">18 мм</SelectItem>
                          <SelectItem value="22">22 мм</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <Button type="submit" className="w-full" disabled={isSubmitting}>
                    {isSubmitting ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Рассчитываем...
                      </>
                    ) : (
                      <>
                        <Check className="mr-2 h-4 w-4" />
                        Рассчитать деталировку
                      </>
                    )}
                  </Button>
                </form>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* AI Fallback CTA */}
        <div className="mt-8 p-4 bg-muted rounded-lg text-center">
          <p className="text-sm text-muted-foreground mb-2">
            Сложный заказ или нужна консультация?
          </p>
          <Button variant="link" asChild className="p-0 h-auto">
            <Link href="/new/dialogue" className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4" />
              Спросить AI-технолога
            </Link>
          </Button>
        </div>

        {/* Назад */}
        <div className="mt-8 text-center">
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
