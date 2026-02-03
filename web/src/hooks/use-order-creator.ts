"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import type {
  OrderCreatorMode,
  OrderCreatorParams,
  FieldSource,
  ImageExtractResponse,
  ChatMessage,
} from "@/types/api";

interface OrderCreatorState {
  mode: OrderCreatorMode;
  params: Partial<OrderCreatorParams>;
  fieldSources: Record<string, FieldSource>;
  orderId: string | null;
  chatMessages: ChatMessage[];
  error: string | null;
  isLoading: boolean;
  recognizedCount: number;
  suggestedPrompt: string | null;
}

const DEFAULT_PARAMS: Partial<OrderCreatorParams> = {
  cabinet_type: "",
  width_mm: undefined,
  height_mm: undefined,
  depth_mm: undefined,
  material: "ЛДСП",
  thickness_mm: 16,
  door_count: 1,
  drawer_count: 0,
  shelf_count: 1,
};

export function useOrderCreator() {
  const router = useRouter();

  const [state, setState] = useState<OrderCreatorState>({
    mode: "upload",
    params: DEFAULT_PARAMS,
    fieldSources: {},
    orderId: null,
    chatMessages: [],
    error: null,
    isLoading: false,
    recognizedCount: 0,
    suggestedPrompt: null,
  });

  // Переход в режим manual
  const goToManual = useCallback(() => {
    setState((prev) => ({
      ...prev,
      mode: "manual",
      error: null,
    }));
  }, []);

  // Загрузка и анализ фото
  const analyzePhoto = useCallback(async (file: File) => {
    setState((prev) => ({ ...prev, mode: "processing", isLoading: true, error: null }));

    try {
      const base64 = await fileToBase64(file);

      const response = await fetch("/api/v1/spec/extract-from-image", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          image_base64: base64,
          image_mime_type: file.type,
          language_hint: "ru",
        }),
      });

      if (!response.ok) {
        throw new Error("Ошибка распознавания");
      }

      const data: ImageExtractResponse = await response.json();

      if (!data.success) {
        setState((prev) => ({
          ...prev,
          mode: "manual",
          error: data.error || "Не удалось распознать изображение",
          isLoading: false,
        }));
        return;
      }

      // Конвертируем параметры
      const params = extractParamsFromResponse(data);
      const fieldSources = data.field_sources || {};

      // Порог: ≥3 полей распознано → review, <3 → clarify
      const nextMode: OrderCreatorMode = data.recognized_count >= 3 ? "review" : "clarify";

      setState((prev) => ({
        ...prev,
        mode: nextMode,
        params,
        fieldSources,
        recognizedCount: data.recognized_count,
        suggestedPrompt: data.suggested_prompt,
        isLoading: false,
      }));
    } catch (err) {
      setState((prev) => ({
        ...prev,
        mode: "manual",
        error: err instanceof Error ? err.message : "Неизвестная ошибка",
        isLoading: false,
      }));
    }
  }, []);

  // Обновление параметра пользователем
  const updateParam = useCallback((key: keyof OrderCreatorParams, value: unknown) => {
    setState((prev) => ({
      ...prev,
      params: { ...prev.params, [key]: value },
      fieldSources: { ...prev.fieldSources, [key]: "user" as FieldSource },
    }));
  }, []);

  // Переход в режим clarify
  const openClarify = useCallback(() => {
    setState((prev) => ({ ...prev, mode: "clarify" }));
  }, []);

  // Закрытие clarify
  const closeClarify = useCallback(() => {
    setState((prev) => ({ ...prev, mode: "review" }));
  }, []);

  // Обновление параметров из AI-чата
  const updateFromAI = useCallback((updates: Partial<OrderCreatorParams>) => {
    setState((prev) => {
      const newFieldSources = { ...prev.fieldSources };
      Object.keys(updates).forEach((key) => {
        newFieldSources[key] = "ai" as FieldSource;
      });

      return {
        ...prev,
        params: { ...prev.params, ...updates },
        fieldSources: newFieldSources,
        mode: "review",
      };
    });
  }, []);

  // Подтверждение и создание заказа
  const confirm = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true }));

    try {
      // Создать заказ
      const orderResponse = await fetch("/api/v1/orders/anonymous", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: state.params.cabinet_type || "Новый заказ",
          description: "Создан через Vision OCR",
          spec: state.params,
        }),
      });

      if (!orderResponse.ok) {
        throw new Error("Ошибка создания заказа");
      }

      const order = await orderResponse.json();

      // Сгенерировать BOM
      const bomResponse = await fetch("/api/v1/bom/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          order_id: order.id,
          cabinet_type: state.params.cabinet_type || "base",
          width_mm: state.params.width_mm || 600,
          height_mm: state.params.height_mm || 720,
          depth_mm: state.params.depth_mm || 560,
          material: `${state.params.material || "ЛДСП"} ${state.params.thickness_mm || 16}мм`,
          shelf_count: state.params.shelf_count || 1,
          door_count: state.params.door_count || 1,
          drawer_count: state.params.drawer_count || 0,
        }),
      });

      if (!bomResponse.ok) {
        console.error("BOM generation failed");
      }

      router.push(`/bom?orderId=${order.id}`);
    } catch (err) {
      setState((prev) => ({
        ...prev,
        error: err instanceof Error ? err.message : "Ошибка",
        isLoading: false,
      }));
    }
  }, [state.params, router]);

  // Добавление сообщения в чат
  const addChatMessage = useCallback((message: ChatMessage) => {
    setState((prev) => ({
      ...prev,
      chatMessages: [...prev.chatMessages, message],
    }));
  }, []);

  return {
    ...state,
    analyzePhoto,
    updateParam,
    goToManual,
    openClarify,
    closeClarify,
    updateFromAI,
    confirm,
    addChatMessage,
  };
}

// ============================================================================
// Утилиты
// ============================================================================

/**
 * Конвертирует File в base64 строку
 */
async function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const base64 = (reader.result as string).split(",")[1];
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

/**
 * Извлекает параметры из ответа Vision OCR API
 */
function extractParamsFromResponse(data: ImageExtractResponse): Partial<OrderCreatorParams> {
  const p = data.parameters;
  if (!p) return DEFAULT_PARAMS;

  return {
    cabinet_type: p.furniture_type?.category || "",
    width_mm: p.dimensions?.width_mm ?? undefined,
    height_mm: p.dimensions?.height_mm ?? undefined,
    depth_mm: p.dimensions?.depth_mm ?? undefined,
    material: p.body_material?.type || "ЛДСП",
    thickness_mm: p.dimensions?.thickness_mm ?? 16,
    door_count: p.door_count ?? 1,
    drawer_count: p.drawer_count ?? 0,
    shelf_count: p.shelf_count ?? 1,
  };
}
