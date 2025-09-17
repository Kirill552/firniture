'use client'

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Search } from "lucide-react"
import { AiExplanation } from "@/components/ai-explanation"
import { HardwareComparisonModal } from "@/components/hardware-comparison-modal"

// This is a placeholder for the actual hardware item type
type HardwareItem = {
  sku: string;
  name: string;
  description: string;
  imageUrl: string;
  aiExplanation: {
    pros: string[];
    cons: string[];
    confidence: number;
  };
  [key: string]: any; // Allow other properties
};

const hardwareItems: HardwareItem[] = [
  {
    sku: "HFL-001",
    name: "Петля накладная, 110°",
    description: "Стандартная петля для большинства фасадов. Простая установка.",
    imageUrl: "/placeholder.svg",
    aiExplanation: {
      pros: ["Надежная", "Низкая стоимость"],
      cons: ["Не для толстых фасадов"],
      confidence: 0.95,
    },
  },
  {
    sku: "HFL-002",
    name: "Петля для фальш-панелей, 90°",
    description: "Используется для угловых шкафов и фальш-панелей.",
    imageUrl: "/placeholder.svg",
    aiExplanation: {
      pros: ["Решает проблему угловых соединений"],
      cons: ["Сложнее в установке"],
      confidence: 0.88,
    },
  },
  {
    sku: "DRS-010",
    name: "Направляющие шариковые, 450мм",
    description: "Плавное и тихое выдвижение ящиков. Полное выдвижение.",
    imageUrl: "/placeholder.svg",
    aiExplanation: {
      pros: ["Плавный ход", "Высокая нагрузка"],
      cons: ["Требуют точной установки"],
      confidence: 0.92,
    },
  },
]

export default function HardwarePage() {
  const [selectedItems, setSelectedItems] = useState<HardwareItem[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleSelectItem = (item: HardwareItem) => {
    setSelectedItems(prev => 
      prev.find(i => i.sku === item.sku) 
        ? prev.filter(i => i.sku !== item.sku) 
        : [...prev, item]
    );
  };

  const isSelected = (item: HardwareItem) => !!selectedItems.find(i => i.sku === item.sku);

  return (
    <div className="p-6 w-full">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Подбор фурнитуры</h1>
        <Button onClick={() => setIsModalOpen(true)} disabled={selectedItems.length < 2}>
          Сравнить выбранное ({selectedItems.length})
        </Button>
      </div>

      <div className="relative mb-6">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
        <Input placeholder="Поиск по названию, SKU или параметрам..." className="pl-10" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {hardwareItems.map((item) => (
          <Card key={item.sku} className={`flex flex-col ${isSelected(item) ? 'border-primary' : ''}`}>
            <CardHeader>
              <img src={item.imageUrl} alt={item.name} className="rounded-lg mb-4 h-40 w-full object-cover" />
              <CardTitle>{item.name}</CardTitle>
              <CardDescription>{item.sku}</CardDescription>
            </CardHeader>
            <CardContent className="flex-grow">
              <p className="mb-4 text-sm">{item.description}</p>
              <AiExplanation {...item.aiExplanation} />
            </CardContent>
            <div className="p-6 pt-0">
                <Button variant={isSelected(item) ? "secondary" : "outline"} className="w-full" onClick={() => handleSelectItem(item)}>
                  {isSelected(item) ? "Убрать из сравнения" : "Добавить к сравнению"}
                </Button>
            </div>
          </Card>
        ))}
      </div>
      <HardwareComparisonModal items={selectedItems} open={isModalOpen} onOpenChange={setIsModalOpen} />
    </div>
  )
}

