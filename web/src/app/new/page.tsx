"use client";

import { useOrderCreator } from "@/hooks/use-order-creator";
import { FileDropzone } from "@/components/vision/file-dropzone";
import {
  ParamsReviewCard,
  TypeSelector,
  InlineChatPanel,
} from "@/components/order-creator";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Loader2, Keyboard, Check, ArrowLeft } from "lucide-react";
import Link from "next/link";

const MATERIALS = [
  { value: "ЛДСП", label: "ЛДСП" },
  { value: "МДФ", label: "МДФ" },
  { value: "Фанера", label: "Фанера" },
];

const THICKNESSES = [
  { value: "16", label: "16 мм" },
  { value: "18", label: "18 мм" },
  { value: "22", label: "22 мм" },
];

export default function NewOrderPage() {
  const {
    mode,
    params,
    fieldSources,
    error,
    isLoading,
    recognizedCount,
    suggestedPrompt,
    chatMessages,
    orderId,
    analyzePhoto,
    updateParam,
    goToManual,
    openClarify,
    closeClarify,
    updateFromAI,
    confirm,
    addChatMessage,
  } = useOrderCreator();

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/20">
      <div className="container mx-auto px-4 py-12">
        <div className="flex gap-6 max-w-5xl mx-auto">
          {/* Main content */}
          <div className="flex-1 max-w-2xl">
            {/* Header */}
            <div className="mb-8 text-center">
              <h1 className="text-3xl font-bold tracking-tight">Создать заказ</h1>
              <p className="mt-2 text-muted-foreground">
                {mode === "upload" && "Загрузите фото эскиза или введите параметры вручную"}
                {mode === "processing" && "Анализируем изображение..."}
                {mode === "review" && "Проверьте распознанные параметры"}
                {mode === "clarify" && "Уточните параметры с помощью AI"}
                {mode === "manual" && "Введите параметры изделия"}
              </p>
            </div>

            {/* Error */}
            {error && (
              <div className="mb-6 p-4 bg-destructive/10 text-destructive rounded-lg">
                {error}
              </div>
            )}

            {/* Mode: Upload */}
            {mode === "upload" && (
              <>
                <FileDropzone onFileSelect={analyzePhoto} isLoading={false} />
                <div className="mt-6 text-center">
                  <Button variant="link" onClick={goToManual} className="gap-2">
                    <Keyboard className="h-4 w-4" />
                    Ввести вручную
                  </Button>
                </div>
              </>
            )}

            {/* Mode: Processing */}
            {mode === "processing" && (
              <div className="flex flex-col items-center justify-center h-64 gap-4">
                <Loader2 className="h-12 w-12 animate-spin text-primary" />
                <p className="text-lg text-muted-foreground">Анализируем изображение...</p>
              </div>
            )}

            {/* Mode: Review */}
            {mode === "review" && (
              <ParamsReviewCard
                params={params}
                fieldSources={fieldSources}
                recognizedCount={recognizedCount}
                onUpdateParam={updateParam}
                onConfirm={confirm}
                onOpenClarify={openClarify}
                isLoading={isLoading}
              />
            )}

            {/* Mode: Clarify */}
            {mode === "clarify" && (
              <div className="flex gap-6">
                <div className="flex-1">
                  <ParamsReviewCard
                    params={params}
                    fieldSources={fieldSources}
                    recognizedCount={recognizedCount}
                    onUpdateParam={updateParam}
                    onConfirm={confirm}
                    onOpenClarify={() => {}} // Уже открыт
                    isLoading={isLoading}
                  />
                </div>
              </div>
            )}

            {/* Mode: Manual */}
            {mode === "manual" && (
              <Card>
                <CardHeader>
                  <CardTitle>Параметры изделия</CardTitle>
                  <CardDescription>
                    Выберите тип и укажите размеры
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  {/* Type selector */}
                  <div className="space-y-2">
                    <Label>Тип изделия</Label>
                    <TypeSelector
                      value={params.cabinet_type || ""}
                      onChange={(v) => updateParam("cabinet_type", v)}
                    />
                  </div>

                  {/* Dimensions */}
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label>Ширина, мм</Label>
                      <Input
                        type="number"
                        value={params.width_mm || ""}
                        onChange={(e) => updateParam("width_mm", parseInt(e.target.value) || 0)}
                        min={100}
                        max={3000}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Высота, мм</Label>
                      <Input
                        type="number"
                        value={params.height_mm || ""}
                        onChange={(e) => updateParam("height_mm", parseInt(e.target.value) || 0)}
                        min={100}
                        max={3000}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Глубина, мм</Label>
                      <Input
                        type="number"
                        value={params.depth_mm || ""}
                        onChange={(e) => updateParam("depth_mm", parseInt(e.target.value) || 0)}
                        min={100}
                        max={1200}
                      />
                    </div>
                  </div>

                  {/* Material */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Материал</Label>
                      <Select
                        value={params.material || "ЛДСП"}
                        onValueChange={(v) => updateParam("material", v)}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {MATERIALS.map((m) => (
                            <SelectItem key={m.value} value={m.value}>
                              {m.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>Толщина</Label>
                      <Select
                        value={String(params.thickness_mm || 16)}
                        onValueChange={(v) => updateParam("thickness_mm", parseInt(v))}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {THICKNESSES.map((t) => (
                            <SelectItem key={t.value} value={t.value}>
                              {t.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  {/* Submit */}
                  <Button
                    onClick={confirm}
                    disabled={isLoading || !params.cabinet_type}
                    className="w-full"
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Создаём заказ...
                      </>
                    ) : (
                      <>
                        <Check className="mr-2 h-4 w-4" />
                        Рассчитать деталировку
                      </>
                    )}
                  </Button>
                </CardContent>
              </Card>
            )}

            {/* Back link */}
            <div className="mt-8 text-center">
              <Link href="/">
                <Button variant="ghost" size="sm">
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  На главную
                </Button>
              </Link>
            </div>
          </div>

          {/* Inline chat panel (only in clarify mode) */}
          {mode === "clarify" && (
            <InlineChatPanel
              messages={chatMessages}
              suggestedPrompt={suggestedPrompt}
              currentParams={params}
              orderId={orderId}
              onSendMessage={(msg) => {
                addChatMessage({
                  id: Date.now().toString(),
                  role: "user",
                  content: msg,
                  timestamp: new Date(),
                });
              }}
              onParamUpdate={updateFromAI}
              onClose={closeClarify}
              isOpen={true}
            />
          )}
        </div>
      </div>
    </div>
  );
}
