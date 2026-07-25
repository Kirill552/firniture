"use client";

import { useOrderCreator } from "@/hooks/use-order-creator";
import { FileDropzone } from "@/components/vision/file-dropzone";
import {
  ParamsReviewCard,
  TypeSelector,
  InlineChatPanel,
  OrderCreatorShell,
  GuestAuthGate,
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
    isChatLoading,
    recognizedCount,
    suggestedPrompt,
    chatMessages,
    orderId,
    authRequired,
    analyzePhoto,
    updateParam,
    goToManual,
    openClarify,
    closeClarify,
    updateFromAI,
    confirm,
    sendChatMessage,
  } = useOrderCreator();

  return (
    <OrderCreatorShell
      mode={mode}
      chatPanel={
        <InlineChatPanel
          messages={chatMessages}
          suggestedPrompt={suggestedPrompt}
          currentParams={params}
          orderId={orderId}
          onSendMessage={sendChatMessage}
          onParamUpdate={updateFromAI}
          onClose={closeClarify}
          isOpen={true}
          isLoading={isChatLoading}
        />
      }
    >
      {/* Header */}
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-bold tracking-tight text-[#171a1d]">Создать заказ</h1>
        <p className="mt-2 text-[#66707a] text-sm">
          {mode === "upload" && "Загрузите фото эскиза или введите параметры вручную"}
          {mode === "processing" && "Анализируем изображение..."}
          {mode === "review" && "Проверьте распознанные параметры"}
          {mode === "clarify" && "Уточните параметры с помощью AI"}
          {mode === "manual" && "Введите параметры изделия"}
        </p>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-600 rounded-xl text-sm font-medium">
          {error}
        </div>
      )}

      {/* Mode: Upload */}
      {mode === "upload" && (
        <>
          <FileDropzone onFileSelect={analyzePhoto} isLoading={false} data-testid="photo-upload-dropzone" />
          <div className="mt-6 text-center">
            <Button variant="link" onClick={goToManual} className="gap-2 text-[#171a1d] hover:text-[#171a1d]/80 text-sm font-semibold cursor-pointer" data-testid="manual-entry-button">
              <Keyboard className="h-4 w-4" />
              Ввести вручную
            </Button>
          </div>
        </>
      )}

      {/* Mode: Processing */}
      {mode === "processing" && (
        <div className="flex flex-col items-center justify-center h-64 gap-4 bg-white rounded-xl border border-[#d7dde2] p-6 shadow-sm">
          <Loader2 className="h-10 w-10 animate-spin text-[#171a1d]" />
          <p className="text-sm text-[#66707a]">Анализируем изображение...</p>
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
        <ParamsReviewCard
          params={params}
          fieldSources={fieldSources}
          recognizedCount={recognizedCount}
          onUpdateParam={updateParam}
          onConfirm={confirm}
          onOpenClarify={() => {}} // Уже открыт
          isLoading={isLoading}
        />
      )}

      {/* Mode: Manual */}
      {mode === "manual" && (
        <Card className="bg-white border border-[#d7dde2] rounded-xl shadow-sm overflow-hidden">
          <CardHeader className="p-6 pb-4">
            <CardTitle className="text-lg font-bold text-[#171a1d]">Параметры изделия</CardTitle>
            <CardDescription className="text-xs text-[#66707a]">
              Выберите тип и укажите размеры
            </CardDescription>
          </CardHeader>
          <CardContent className="p-6 pt-0 space-y-6">
            {/* Type selector */}
            <div className="space-y-2">
              <Label className="text-xs font-semibold text-[#171a1d]">Тип изделия</Label>
              <TypeSelector
                value={params.cabinet_type || ""}
                onChange={(v) => updateParam("cabinet_type", v)}
              />
            </div>

            {/* Dimensions */}
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold text-[#171a1d]">Ширина, мм</Label>
                <Input
                  type="number"
                  value={params.width_mm != null ? params.width_mm : ""}
                  onChange={(e) => {
                    const str = e.target.value;
                    const n = str === "" ? undefined : parseInt(str);
                    updateParam("width_mm", isNaN(n as number) ? undefined : n);
                  }}
                  min={100}
                  max={3000}
                  className="h-10 border-[#d7dde2] focus-visible:ring-[#c7ff00] text-sm rounded-lg"
                  data-testid="input-width-mm"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold text-[#171a1d]">Высота, мм</Label>
                <Input
                  type="number"
                  value={params.height_mm != null ? params.height_mm : ""}
                  onChange={(e) => {
                    const str = e.target.value;
                    const n = str === "" ? undefined : parseInt(str);
                    updateParam("height_mm", isNaN(n as number) ? undefined : n);
                  }}
                  min={100}
                  max={3000}
                  className="h-10 border-[#d7dde2] focus-visible:ring-[#c7ff00] text-sm rounded-lg"
                  data-testid="input-height-mm"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold text-[#171a1d]">Глубина, мм</Label>
                <Input
                  type="number"
                  value={params.depth_mm != null ? params.depth_mm : ""}
                  onChange={(e) => {
                    const str = e.target.value;
                    const n = str === "" ? undefined : parseInt(str);
                    updateParam("depth_mm", isNaN(n as number) ? undefined : n);
                  }}
                  min={100}
                  max={1200}
                  className="h-10 border-[#d7dde2] focus-visible:ring-[#c7ff00] text-sm rounded-lg"
                  data-testid="input-depth-mm"
                />
              </div>
            </div>

            {/* Material */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold text-[#171a1d]">Материал</Label>
                <Select
                  value={params.material || "ЛДСП"}
                  onValueChange={(v) => updateParam("material", v)}
                >
                  <SelectTrigger className="h-10 border-[#d7dde2] focus:ring-[#c7ff00] text-sm bg-white rounded-lg" data-testid="select-material">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-white border-[#d7dde2] rounded-lg">
                    {MATERIALS.map((m) => (
                      <SelectItem key={m.value} value={m.value} className="text-sm cursor-pointer">
                        {m.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold text-[#171a1d]">Толщина</Label>
                <Select
                  value={String(params.thickness_mm || 16)}
                  onValueChange={(v) => updateParam("thickness_mm", parseInt(v))}
                >
                  <SelectTrigger className="h-10 border-[#d7dde2] focus:ring-[#c7ff00] text-sm bg-white rounded-lg" data-testid="select-thickness-mm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-white border-[#d7dde2] rounded-lg">
                    {THICKNESSES.map((t) => (
                      <SelectItem key={t.value} value={t.value} className="text-sm cursor-pointer">
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
              disabled={
                isLoading ||
                !params.cabinet_type ||
                !params.width_mm ||
                !params.height_mm ||
                !params.depth_mm
              }
              className="w-full h-10 bg-[#c7ff00] hover:bg-[#aee600] text-[#171a1d] font-semibold transition-all duration-150 rounded-lg cursor-pointer text-xs active:scale-[0.98] mt-2"
              data-testid="confirm-manual-button"
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
          <Button variant="ghost" size="sm" className="text-[#66707a] hover:text-[#171a1d] hover:bg-transparent cursor-pointer font-semibold">
            <ArrowLeft className="mr-2 h-4 w-4" />
            На главную
          </Button>
        </Link>
      </div>

      {/* Guest Auth Gate Modal */}
      <GuestAuthGate
        isOpen={authRequired}
        onClose={() => {
          window.location.reload()
        }}
        orderId={orderId}
      />
    </OrderCreatorShell>
  );
}
