"use client"

import { DataTable } from "@/components/data-table";
import { ColumnDef } from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

type BomItem = {
  id: string;
  name: string;
  material: string;
  quantity: number;
  dimensions: string;
};

const bomItems: BomItem[] = [
  { id: "1", name: "Боковая стенка", material: "ЛДСП Egger 16мм", quantity: 2, dimensions: "2400x600" },
  { id: "2", name: "Полка", material: "ЛДСП Egger 16мм", quantity: 5, dimensions: "800x580" },
  { id: "3", name: "Задняя стенка", material: "ДВП", quantity: 1, dimensions: "2400x1800" },
];

const columns: ColumnDef<BomItem>[] = [
  {
    accessorKey: "name",
    header: "Наименование",
  },
  {
    accessorKey: "material",
    header: "Материал",
  },
  {
    accessorKey: "quantity",
    header: "Кол-во",
  },
  {
    accessorKey: "dimensions",
    header: "Размеры (мм)",
  },
];

export default function NewOrderBomPage() {
  const handleApprove = () => {
    // TODO: Handle BOM approval
    console.log("BOM approved");
  };

  return (
    <div className="p-6 w-full">
      <Card className="w-full">
        <CardHeader>
          <CardTitle>Спецификация (BOM)</CardTitle>
          <CardDescription>Шаг 3: Проверьте и утвердите спецификацию</CardDescription>
        </CardHeader>
        <CardContent>
          <DataTable columns={columns} data={bomItems} />
          <div className="flex justify-end mt-6">
            <Button onClick={handleApprove}>Утвердить и перейти к CAM</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
