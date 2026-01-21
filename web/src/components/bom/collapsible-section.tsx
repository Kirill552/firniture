"use client"

import { useState } from "react"
import { ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"

interface CollapsibleSectionProps {
  title: string
  badge?: string
  defaultOpen?: boolean
  children: React.ReactNode
  className?: string
}

export function CollapsibleSection({
  title,
  badge,
  defaultOpen = false,
  children,
  className,
}: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className={className}>
      <CollapsibleTrigger className="flex w-full items-center justify-between py-3 px-4 hover:bg-muted/50 rounded-lg transition-colors">
        <div className="flex items-center gap-2">
          <ChevronRight
            className={cn(
              "h-4 w-4 transition-transform duration-200",
              isOpen && "rotate-90"
            )}
          />
          <span className="font-medium">{title}</span>
          {badge && (
            <span className="text-sm text-muted-foreground">({badge})</span>
          )}
        </div>
      </CollapsibleTrigger>
      <CollapsibleContent className="px-4 pb-4">
        {children}
      </CollapsibleContent>
    </Collapsible>
  )
}
