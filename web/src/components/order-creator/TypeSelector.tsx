// web/src/components/order-creator/TypeSelector.tsx
"use client";

import { cn } from "@/lib/utils";

interface CabinetType {
  id: string;
  name: string;
  description: string;
  icon: string; // Emoji для MVP, потом можно заменить на SVG
}

const CABINET_TYPES: CabinetType[] = [
  { id: "wall", name: "Навесной шкаф", description: "Верхний ярус кухни", icon: "🔲" },
  { id: "base", name: "Напольная тумба", description: "Нижний ярус с дверями", icon: "🗄️" },
  { id: "base_sink", name: "Тумба под мойку", description: "Без дна, с вырезом", icon: "🚰" },
  { id: "drawer", name: "Тумба с ящиками", description: "Выдвижные ящики", icon: "📦" },
  { id: "tall", name: "Пенал", description: "Высокий шкаф", icon: "📐" },
];

interface TypeSelectorProps {
  value: string;
  onChange: (value: string) => void;
}

export function TypeSelector({ value, onChange }: TypeSelectorProps) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
      {CABINET_TYPES.map((type) => (
        <button
          key={type.id}
          type="button"
          onClick={() => onChange(type.id)}
          className={cn(
            "flex flex-col items-center p-4 rounded-lg border-2 transition-all",
            "hover:border-primary/50 hover:bg-primary/5",
            value === type.id
              ? "border-primary bg-primary/10"
              : "border-border bg-background"
          )}
        >
          <span className="text-3xl mb-2">{type.icon}</span>
          <span className="font-medium text-sm">{type.name}</span>
          <span className="text-xs text-muted-foreground text-center mt-1">
            {type.description}
          </span>
        </button>
      ))}
    </div>
  );
}
