"use client"

import { Check, Circle, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

type StepStatus = "completed" | "current" | "pending"

interface Step {
  label: string
  status: StepStatus
}

interface MiniStepperProps {
  steps: Step[]
}

export function MiniStepper({ steps }: MiniStepperProps) {
  return (
    <div className="flex items-center gap-2 text-sm">
      {steps.map((step, index) => (
        <div key={step.label} className="flex items-center gap-2">
          {index > 0 && (
            <span className="text-muted-foreground">→</span>
          )}
          <div className="flex items-center gap-1">
            {step.status === "completed" && (
              <Check className="h-4 w-4 text-green-600" />
            )}
            {step.status === "current" && (
              <Loader2 className="h-4 w-4 text-blue-600 animate-spin" />
            )}
            {step.status === "pending" && (
              <Circle className="h-4 w-4 text-muted-foreground" />
            )}
            <span
              className={cn(
                step.status === "completed" && "text-green-600",
                step.status === "current" && "text-blue-600 font-medium",
                step.status === "pending" && "text-muted-foreground"
              )}
            >
              {step.label}
            </span>
          </div>
        </div>
      ))}
    </div>
  )
}
