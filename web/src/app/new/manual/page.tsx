"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
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
import { useToast } from "@/hooks/use-toast";
import { ArrowLeft, Check, Loader2 } from "lucide-react";

const PRODUCT_TYPES: Record<string, string> = {
  wall: "Навесной шкаф",
  base: "Напольная тумба",
  base_sink: "Тумба под мойку",
  drawer: "Тумба с ящиками",
  tall: "Пенал",
};

export default function ManualOrderPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [formData, setFormData] = useState({
    product_type: "",
    width: "",
    height: "",
    depth: "",
    material: "ЛДСП",
    thickness: "16",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      const width_mm = parseInt(formData.width);
      const height_mm = parseInt(formData.height);
      const depth_mm = parseInt(formData.depth);

      // Параметры для сохранения в заказе
      const specParams = {
        product_type: formData.product_type,
        width: width_mm,
        height: height_mm,
        depth: depth_mm,
        material: formData.material,
        thickness: parseInt(formData.thickness),
      };

      // Создать заказ
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

      // Маппинг для BOM generate endpoint
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

      // Сгенерировать BOM
      const bomResponse = await fetch("/api/v1/bom/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(bomParams),
      });

      if (!bomResponse.ok) {
        console.error("BOM generation failed:", await bomResponse.text());
      }

      // Перейти в BOM
      router.push(`/bom?orderId=${order.id}`);
    } catch (error) {
      toast({
        title: "Ошибка",
        description: "Не удалось создать заказ",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const updateField = (key: string, value: string) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/20">
      <div className="container mx-auto max-w-xl px-4 py-12">
        <Link href="/new">
          <Button variant="ghost" size="sm" className="mb-8">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Назад к выбору
          </Button>
        </Link>

        <Card>
          <CardHeader>
            <CardTitle>Ручной ввод параметров</CardTitle>
            <CardDescription>
              Введите размеры и материалы, и мы рассчитаем деталировку
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
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
      </div>
    </div>
  );
}
