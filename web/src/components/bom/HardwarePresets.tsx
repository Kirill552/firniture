"use client";

import { useState, useEffect } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface HingeTemplate {
  id: string;
  name: string;
  type: string;
  cup_diameter_mm: number;
}

interface SlideTemplate {
  id: string;
  name: string;
  type: string;
  load_capacity_kg: number;
  profile_height_mm: number;
}

interface HardwarePresetsProps {
  hingeTemplate: string;
  slideTemplate: string;
  onHingeChange: (templateId: string) => void;
  onSlideChange: (templateId: string) => void;
  className?: string;
}

export function HardwarePresets({
  hingeTemplate,
  slideTemplate,
  onHingeChange,
  onSlideChange,
  className,
}: HardwarePresetsProps) {
  const [hingeTemplates, setHingeTemplates] = useState<HingeTemplate[]>([]);
  const [slideTemplates, setSlideTemplates] = useState<SlideTemplate[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Загрузка шаблонов
  useEffect(() => {
    const fetchTemplates = async () => {
      try {
        const response = await fetch("/api/v1/hardware/templates");
        if (response.ok) {
          const data = await response.json();
          setHingeTemplates(data.hinges || []);
          setSlideTemplates(data.slides || []);
        }
      } catch (error) {
        console.error("Failed to fetch templates:", error);
        // Fallback данные
        setHingeTemplates([
          { id: "hinge_35mm_overlay", name: "Накладная", type: "overlay", cup_diameter_mm: 35 },
          { id: "hinge_35mm_half_overlay", name: "Полунакладная", type: "half_overlay", cup_diameter_mm: 35 },
          { id: "hinge_35mm_inset", name: "Вкладная", type: "inset", cup_diameter_mm: 35 },
        ]);
        setSlideTemplates([
          { id: "slide_ball_h45", name: "Шариковые H45 (45кг)", type: "ball_h45", load_capacity_kg: 45, profile_height_mm: 45 },
          { id: "slide_ball_h35", name: "Шариковые H35 (35кг)", type: "ball_h35", load_capacity_kg: 35, profile_height_mm: 35 },
          { id: "slide_roller", name: "Роликовые (20кг)", type: "roller", load_capacity_kg: 20, profile_height_mm: 17 },
        ]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchTemplates();
  }, []);

  const selectedHinge = hingeTemplates.find((t) => t.id === hingeTemplate);
  const selectedSlide = slideTemplates.find((t) => t.id === slideTemplate);

  return (
    <Card className={className}>
      <CardHeader className="py-3">
        <CardTitle className="text-sm font-medium">Тип фурнитуры</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Направляющие — Приоритет #1 */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="slide-select" className="text-sm">
              Направляющие
            </Label>
            {selectedSlide && (
              <Badge variant="secondary" className="text-xs">
                до {selectedSlide.load_capacity_kg} кг
              </Badge>
            )}
          </div>
          <Select
            value={slideTemplate}
            onValueChange={onSlideChange}
            disabled={isLoading}
          >
            <SelectTrigger id="slide-select">
              <SelectValue placeholder="Выберите тип" />
            </SelectTrigger>
            <SelectContent>
              {slideTemplates.map((template) => (
                <SelectItem key={template.id} value={template.id}>
                  {template.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Петли */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="hinge-select" className="text-sm">
              Петли
            </Label>
            {selectedHinge && (
              <Badge variant="secondary" className="text-xs">
                ø{selectedHinge.cup_diameter_mm}мм
              </Badge>
            )}
          </div>
          <Select
            value={hingeTemplate}
            onValueChange={onHingeChange}
            disabled={isLoading}
          >
            <SelectTrigger id="hinge-select">
              <SelectValue placeholder="Выберите тип" />
            </SelectTrigger>
            <SelectContent>
              {hingeTemplates.map((template) => (
                <SelectItem key={template.id} value={template.id}>
                  {template.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </CardContent>
    </Card>
  );
}
