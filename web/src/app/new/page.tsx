"use client";

import { useState } from "react";
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
import { ProductPreview } from "@/components/order/product-preview";
import type { ModuleShape } from "@/components/order/module-drawing";

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

const MODULE_TYPES = [
  { type: "wall", label: "Навесной шкаф", width: 600, height: 720 },
  { type: "base", label: "Напольная тумба", width: 600, height: 850 },
  { type: "base_sink", label: "Тумба под мойку", width: 600, height: 850 },
  { type: "drawer", label: "Тумба с ящиками", width: 600, height: 850 },
  { type: "tall", label: "Пенал", width: 600, height: 2200 },
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

  const [wallWidth, setWallWidth] = useState(3000);
  const [ceilingHeight, setCeilingHeight] = useState(2600);
  const [modules, setModules] = useState<ModuleShape[]>([]);
  const [selectedModule, setSelectedModule] = useState(0);
  const modulesWidth = modules.reduce((sum, module) => sum + module.width, 0);
  const widthDifference = wallWidth - modulesWidth;

  const addModule = (moduleType: (typeof MODULE_TYPES)[number]) => {
    const added: ModuleShape = {
      ...moduleType,
      depth: moduleType.type === "wall" ? 320 : 600,
      shelves: moduleType.type === "tall" ? 4 : 1,
      doors: moduleType.width > 700 ? 2 : 1,
      legs: moduleType.type === "wall" ? 0 : 100,
      thickness: params.thickness_mm ?? 16,
    };
    setModules((current) => [...current, added]);
    // Добавленный модуль сразу становится текущим: и на пироге, и в полях ниже.
    setSelectedModule(modules.length);
    updateParam("cabinet_type", added.type);
    updateParam("width_mm", added.width);
    updateParam("height_mm", added.height);
    updateParam("depth_mm", added.depth);
    updateParam("shelf_count", added.shelves);
    updateParam("door_count", added.doors);
  };

  // Поля ниже всегда описывают тот модуль, который выбран на пироге.
  // Иначе картинка показывает пенал, а размеры под ней — от тумбы.
  const selectModule = (index: number) => {
    const target = modules[index];
    if (!target) return;
    setSelectedModule(index);
    updateParam("cabinet_type", target.type);
    updateParam("width_mm", target.width);
    updateParam("height_mm", target.height);
    updateParam("depth_mm", target.depth);
    updateParam("shelf_count", target.shelves);
    updateParam("door_count", target.doors);
  };

  const updateModule = (index: number, patch: Partial<ModuleShape>) => {
    setModules((current) =>
      current.map((module, i) => (i === index ? { ...module, ...patch } : module))
    );
    if (index === selectedModule) {
      if (patch.shelves !== undefined) updateParam("shelf_count", patch.shelves);
      if (patch.doors !== undefined) updateParam("door_count", patch.doors);
    }
  };
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
            <Button variant="link" onClick={goToManual} className="gap-2 text-foreground hover:text-foreground/80 text-sm font-semibold cursor-pointer" data-testid="manual-entry-button">
              <Keyboard className="h-4 w-4" />
              Ввести вручную
            </Button>
          </div>
        </>
      )}

      {/* Mode: Processing */}
      {mode === "processing" && (
        <div className="flex flex-col items-center justify-center h-64 gap-4 bg-card rounded-xl border border-border p-6 shadow-sm">
          <Loader2 className="h-10 w-10 animate-spin text-foreground" />
          <p className="text-sm text-muted-foreground">Анализируем изображение...</p>
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
        <Card className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
          <CardHeader className="p-6 pb-4">
            <CardTitle className="text-lg font-bold text-foreground">Параметры изделия</CardTitle>
            <CardDescription className="text-xs text-muted-foreground">
            </CardDescription>
          </CardHeader>
          <CardContent className="p-6 pt-0 space-y-6">
            <div className="rounded-lg border border-border bg-muted/30 p-4 space-y-3">
              <p className="text-sm font-semibold">Габарит по стене</p>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-xs">Ширина стены, мм</Label>
                  <Input type="number" value={wallWidth} onChange={(e) => setWallWidth(Number(e.target.value) || 0)} />
                </div>
                <div>
                  <Label className="text-xs">Высота потолка, мм</Label>
                  <Input type="number" value={ceilingHeight} onChange={(e) => setCeilingHeight(Number(e.target.value) || 0)} />
                </div>
              </div>
              <p className="text-xs text-muted-foreground">Глубина по умолчанию — 600 мм.</p>
              <div className="flex flex-wrap gap-2">
                {MODULE_TYPES.map((moduleType) => (
                  <Button key={moduleType.type} type="button" variant="outline" size="sm" onClick={() => addModule(moduleType)}>
                    + {moduleType.label}
                  </Button>
                ))}
              </div>
            </div>

            {/* Пирог: что получится до расчёта */}
            <div className="space-y-2">
              <Label className="text-xs font-semibold text-[#171a1d]">Что получится</Label>
              <ProductPreview
                modules={modules}
                wallWidth={wallWidth}
                selectedIndex={selectedModule}
                onSelect={selectModule}
                onChange={updateModule}
              />
            </div>
            {/* Тип изделия нужен, только пока модулей нет: дальше тип задаёт
                выбранный модуль на пироге, и два разных выбора путали бы. */}
            {modules.length === 0 && (
              <div className="space-y-2">
                <Label className="text-xs font-semibold text-[#171a1d]">Тип изделия</Label>
                <TypeSelector
                  value={params.cabinet_type || ""}
                  onChange={(v) => updateParam("cabinet_type", v)}
                />
              </div>
            )}

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
                  className="h-10 border-border focus-visible:ring-ring text-sm rounded-lg"
                  data-testid="input-width-mm"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold text-foreground">Высота, мм</Label>
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
                  className="h-10 border-border focus-visible:ring-ring text-sm rounded-lg"
                  data-testid="input-height-mm"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold text-foreground">Глубина, мм</Label>
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
                  className="h-10 border-border focus-visible:ring-ring text-sm rounded-lg"
                  data-testid="input-depth-mm"
                />
              </div>
            </div>

            {/* Material */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold text-foreground">Материал</Label>
                <Select
                  value={params.material || "ЛДСП"}
                  onValueChange={(v) => updateParam("material", v)}
                >
                  <SelectTrigger className="h-10 border-border focus:ring-ring text-sm bg-card rounded-lg" data-testid="select-material">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-card border-border rounded-lg">
                    {MATERIALS.map((m) => (
                      <SelectItem key={m.value} value={m.value} className="text-sm cursor-pointer">
                        {m.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold text-foreground">Толщина</Label>
                <Select
                  value={String(params.thickness_mm || 16)}
                  onValueChange={(v) => updateParam("thickness_mm", parseInt(v))}
                >
                  <SelectTrigger className="h-10 border-border focus:ring-ring text-sm bg-card rounded-lg" data-testid="select-thickness-mm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-card border-border rounded-lg">
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
              className="w-full h-10 cursor-pointer text-xs mt-2"
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
                  Сгенерировать технологию
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Back link */}
      <div className="mt-8 text-center">
        <Link href="/">
          <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground hover:bg-transparent cursor-pointer font-semibold">
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
