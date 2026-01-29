"use client";

import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertTriangle } from "lucide-react";

interface ConfirmationCheckboxProps {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  className?: string;
}

export function ConfirmationCheckbox({
  checked,
  onCheckedChange,
  className,
}: ConfirmationCheckboxProps) {
  return (
    <div className={className}>
      <Alert variant={checked ? "default" : "destructive"} className="mb-4">
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription className="text-sm">
          Перед скачиванием файлов убедитесь в правильности спецификации.
          Итоговая проверка — ответственность пользователя.
        </AlertDescription>
      </Alert>

      <div className="flex items-start space-x-3 p-4 border rounded-lg bg-muted/50">
        <Checkbox
          id="confirmation"
          checked={checked}
          onCheckedChange={(value) => onCheckedChange(value === true)}
          className="mt-0.5"
        />
        <Label
          htmlFor="confirmation"
          className="text-sm font-medium leading-relaxed cursor-pointer"
        >
          Я проверил спецификацию и подтверждаю корректность размеров,
          количества фурнитуры и координат присадки.
        </Label>
      </div>
    </div>
  );
}
