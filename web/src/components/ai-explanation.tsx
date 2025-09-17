'use client'

import { Card } from "@/components/ui/card"

interface AiExplanationProps {
  pros: string[];
  cons: string[];
  confidence: number;
}

export function AiExplanation({ pros, cons, confidence }: AiExplanationProps) {
  const confidenceColor = confidence > 0.9 ? "bg-green-500" : confidence > 0.75 ? "bg-yellow-500" : "bg-red-500";

  return (
    <Card className="bg-gray-100 dark:bg-gray-800 p-3 rounded-lg">
      <div className="flex justify-between items-center mb-2">
        <h4 className="font-semibold text-sm">AI-анализ</h4>
        <div className="flex items-center">
          <span className={`w-3 h-3 rounded-full mr-2 ${confidenceColor}`}></span>
          <span className="text-xs text-muted-foreground">Уверенность: {Math.round(confidence * 100)}%</span>
        </div>
      </div>
      <div>
        {pros.map((pro, i) => <p key={i} className="text-xs text-green-600">+ {pro}</p>)}
        {cons.map((con, i) => <p key={i} className="text-xs text-red-600">- {con}</p>)}
      </div>
    </Card>
  )
}
