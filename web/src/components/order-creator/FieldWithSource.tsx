// web/src/components/order-creator/FieldWithSource.tsx
"use client";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Check, AlertTriangle, Camera, Bot, User } from "lucide-react";
import type { FieldSource } from "@/types/api";
import { cn } from "@/lib/utils";

interface FieldWithSourceProps {
  label: string;
  value: string | number | undefined;
  source: FieldSource | undefined;
  onChange: (value: string | number) => void;
  unit?: string;
  type?: "text" | "number" | "select";
  options?: { value: string; label: string }[];
  placeholder?: string;
  min?: number;
  max?: number;
}

const SOURCE_CONFIG: Record<FieldSource, { icon: typeof Check; color: string; label: string }> = {
  ocr: { icon: Camera, color: "text-green-600", label: "Распознано с фото" },
  inferred: { icon: Check, color: "text-blue-600", label: "Выведено из контекста" },
  default: { icon: AlertTriangle, color: "text-amber-500", label: "Значение по умолчанию" },
  user: { icon: User, color: "text-green-600", label: "Введено вами" },
  ai: { icon: Bot, color: "text-purple-600", label: "Уточнено AI" },
};

export function FieldWithSource({
  label,
  value,
  source = "default",
  onChange,
  unit,
  type = "text",
  options,
  placeholder,
  min,
  max,
}: FieldWithSourceProps) {
  const config = SOURCE_CONFIG[source];
  const Icon = config.icon;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-2">
        <Label className="text-sm font-medium">{label}</Label>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Icon className={cn("h-3.5 w-3.5", config.color)} />
            </TooltipTrigger>
            <TooltipContent>
              <p>{config.label}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      <div className="relative">
        {type === "select" && options ? (
          <Select
            value={String(value || "")}
            onValueChange={(v) => onChange(v)}
          >
            <SelectTrigger className={cn(
              source === "default" && "border-amber-300 bg-amber-50/50"
            )}>
              <SelectValue placeholder={placeholder} />
            </SelectTrigger>
            <SelectContent>
              {options.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : (
          <div className="relative">
            <Input
              type={type}
              value={value ?? ""}
              onChange={(e) => {
                const v = type === "number" ? parseInt(e.target.value) || 0 : e.target.value;
                onChange(v);
              }}
              placeholder={placeholder}
              min={min}
              max={max}
              className={cn(
                source === "default" && "border-amber-300 bg-amber-50/50",
                unit && "pr-12"
              )}
            />
            {unit && (
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground">
                {unit}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
