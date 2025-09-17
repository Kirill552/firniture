'use client'

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

// This is a placeholder for the actual hardware item type
type HardwareItem = {
  sku: string;
  name: string;
  description: string;
  [key: string]: any; // Allow other properties
};

interface HardwareComparisonModalProps {
  items: HardwareItem[];
  onOpenChange: (open: boolean) => void;
  open: boolean;
}

export function HardwareComparisonModal({ items, onOpenChange, open }: HardwareComparisonModalProps) {
  if (items.length === 0) return null

  const allKeys = Array.from(new Set(items.flatMap(item => Object.keys(item))))
    .filter(key => !["imageUrl", "aiExplanation"].includes(key));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <DialogTitle>Сравнение фурнитуры</DialogTitle>
          <DialogDescription>
            Сравнение характеристик выбранных элементов.
          </DialogDescription>
        </DialogHeader>
        <div className="overflow-auto">
            <Table>
            <TableHeader>
                <TableRow>
                <TableHead className="font-bold">Характеристика</TableHead>
                {items.map(item => <TableHead key={item.sku}>{item.name}</TableHead>)}
                </TableRow>
            </TableHeader>
            <TableBody>
                {allKeys.map(key => (
                <TableRow key={key}>
                    <TableCell className="font-semibold">{key}</TableCell>
                    {items.map(item => <TableCell key={item.sku}>{String(item[key] ?? '-')}</TableCell>)}
                </TableRow>
                ))}
            </TableBody>
            </Table>
        </div>
      </DialogContent>
    </Dialog>
  )
}
