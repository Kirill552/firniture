"use client";

import { useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { getAuthHeader } from "@/lib/auth";
import { getUploadErrorMessage } from "./upload-errors";
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
  isChatLoading: boolean;
  recognizedCount: number;
  suggestedPrompt: string | null;
  // Гостевой grant хранится только в памяти текущего сценария, не в localStorage.
  guestUploadGrant: string | null;
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
  const creatingOrderRef = useRef<Promise<string> | null>(null);

  const [state, setState] = useState<OrderCreatorState>({
    mode: "upload",
    params: DEFAULT_PARAMS,
    fieldSources: {},
    orderId: null,
    chatMessages: [],
    error: null,
    isLoading: false,
    isChatLoading: false,
    recognizedCount: 0,
    suggestedPrompt: null,
    guestUploadGrant: null,
  });

  const createAnonymousOrder = useCallback(async (grant?: string | null): Promise<string> => {
    const authHeader = getAuthHeader();
    const isAuthed = !!authHeader.Authorization;
    const endpoint = isAuthed ? "/api/v1/orders" : "/api/v1/orders/anonymous";

    let effectiveGrant = grant;
    if (!isAuthed && !effectiveGrant) {
      const grantResponse = await fetch("/api/v1/orders/anonymous/grant", { method: "POST" });
      if (!grantResponse.ok) {
        const payload = await grantResponse.json().catch(() => null);
        throw new Error(getUploadErrorMessage(grantResponse.status, payload));
      }
      const grantPayload = await grantResponse.json() as { guest_upload_grant?: string };
      effectiveGrant = grantPayload.guest_upload_grant ?? null;
    }

    const headers: Record<string, string> = { "Content-Type": "application/json", ...authHeader };
    if (!isAuthed && effectiveGrant) {
      headers["X-Guest-Upload-Grant"] = effectiveGrant;
    }

    const response = await fetch(endpoint, {
      method: "POST",
      headers,
      body: JSON.stringify({
        notes: "Черновик (Vision OCR / ручной ввод)",
      }),
    });

    if (!response.ok) {
      const txt = await response.text().catch(() => "");
      throw new Error(txt || "Не удалось создать заказ для AI-диалога");
    }

    const order = await response.json();
    const orderId = String(order.id);

    setState((prev) => ({
      ...prev,
      orderId,
    }));

    return orderId;
  }, []);

  // Создаём заказ один раз на сессию создания (нужен для /dialogue/clarify и BOM/CAM).
  // Если пользователь авторизован - создаём /orders, иначе /orders/anonymous (freemium) с grant.
  const ensureAnonymousOrder = useCallback(async (): Promise<string> => {
    if (state.orderId) return state.orderId;
    if (creatingOrderRef.current) return creatingOrderRef.current;

    creatingOrderRef.current = (async () => {
      return await createAnonymousOrder(state.guestUploadGrant);
    })();

    try {
      return await creatingOrderRef.current;
    } finally {
      creatingOrderRef.current = null;
    }
  }, [createAnonymousOrder, state.orderId, state.guestUploadGrant]);

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
    // Сброс состояния под новый заказ: диалог не должен "наследовать" историю из прошлого orderId.
    creatingOrderRef.current = null;
    setState((prev) => ({
      ...prev,
      mode: "processing",
      isLoading: true,
      error: null,
      orderId: null,
      chatMessages: [],
      suggestedPrompt: null,
      recognizedCount: 0,
      fieldSources: {},
      guestUploadGrant: null,
    }));

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
        const payload = await response.json().catch(() => null);
        throw new Error(getUploadErrorMessage(response.status, payload));
      }

      const data: ImageExtractResponse = await response.json();

      if (!data.success) {
        setState((prev) => ({
          ...prev,
          mode: "manual",
          error: data.error || "Не удалось распознать изображение",
          isLoading: false,
          guestUploadGrant: null,
        }));
        return;
      }

      // Сохраняем grant ТОЛЬКО в памяти (для передачи при создании anonymous)
      const grant = data.guest_upload_grant || null;
      if (!grant) {
        throw new Error("Проверка завершилась без разрешения на создание заказа. Повторите загрузку.");
      }

      // Конвертируем параметры
      const params = extractParamsFromResponse(data);
      const fieldSources = normalizeFieldSources(data.field_sources || undefined);

      // Если категорию OCR мы не смогли нормализовать в cabinet_type — помечаем как default.
      if (!params.cabinet_type) {
        fieldSources.cabinet_type = "default";
      }

      // Если ключевых параметров (тип + габариты) не хватает — сразу уводим в уточнение.
      const nextMode: OrderCreatorMode = areRequiredParamsReady(params) ? "review" : "clarify";

      setState((prev) => ({
        ...prev,
        mode: nextMode,
        params,
        fieldSources,
        orderId: null,
        chatMessages: [],
        recognizedCount: data.recognized_count,
        suggestedPrompt: data.suggested_prompt ?? null,
        isLoading: false,
        guestUploadGrant: grant,
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
  const openClarify = useCallback(async () => {
    setState((prev) => ({ ...prev, error: null }));
    try {
      const orderId = await ensureAnonymousOrder();
      setState((prev) => ({ ...prev, orderId, mode: "clarify" }));
    } catch (err) {
      setState((prev) => ({
        ...prev,
        error: err instanceof Error ? err.message : "Не удалось открыть AI-уточнение",
      }));
    }
  }, [ensureAnonymousOrder]);

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
        // Режим не переключаем: пользователь сам закрывает панель уточнения.
      };
    });
  }, []);

  // Отправка сообщения в AI-чат (inline уточнение).
  const sendChatMessage = useCallback(async (message: string) => {
    const text = message.trim();
    if (!text) return;

    setState((prev) => ({
      ...prev,
      isChatLoading: true,
      error: null,
      chatMessages: [
        ...prev.chatMessages,
        {
          id: Date.now().toString(),
          role: "user",
          content: text,
          timestamp: new Date(),
        },
      ],
    }));

    try {
      const orderId = await ensureAnonymousOrder();

      const response = await fetch("/api/v1/dialogue/clarify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          order_id: orderId,
          messages: [{ role: "user", content: text }],
          current_params: toDialogueCurrentParams(state.params),
        }),
      });

      if (!response.ok) {
        throw new Error("Ошибка AI-уточнения");
      }

      const raw = await response.text();
      const parsed = parseAssistantParamUpdates(raw);

      if (parsed.updates) {
        updateFromAI(parsed.updates);
      }

      if (parsed.text) {
        setState((prev) => ({
          ...prev,
          chatMessages: [
            ...prev.chatMessages,
            {
              id: (Date.now() + 1).toString(),
              role: "assistant",
              content: parsed.text,
              timestamp: new Date(),
            },
          ],
        }));
      }
    } catch (err) {
      setState((prev) => ({
        ...prev,
        error: err instanceof Error ? err.message : "Ошибка AI-диалога",
      }));
    } finally {
      setState((prev) => ({ ...prev, isChatLoading: false }));
    }
  }, [ensureAnonymousOrder, state.params, updateFromAI]);

  // Подтверждение и создание заказа
  const confirm = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true }));

    try {
      if (!areRequiredParamsReady(state.params)) {
        throw new Error("Укажите тип изделия и габариты (Ш×В×Г), чтобы рассчитать деталировку");
      }

      // Используем уже созданный заказ (для OCR/диалога), либо создаём новый.
      const orderId = state.orderId || (await ensureAnonymousOrder());

      // Сгенерировать BOM
      const bomResponse = await fetch("/api/v1/bom/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          order_id: orderId,
          cabinet_type: state.params.cabinet_type || "base",
          width_mm: state.params.width_mm || 600,
          height_mm: state.params.height_mm || 720,
          depth_mm: state.params.depth_mm || 560,
          material: state.params.material || "ЛДСП",
          thickness_mm: state.params.thickness_mm || 16,
          shelf_count: state.params.shelf_count || 1,
          door_count: state.params.door_count || 1,
          drawer_count: state.params.drawer_count || 0,
        }),
      });

      if (!bomResponse.ok) {
        const errText = await bomResponse.text();
        throw new Error(errText || "Не удалось сформировать спецификацию");
      }

      // Reset loading before navigation (component will unmount)
      setState((prev) => ({ ...prev, isLoading: false }));
      router.push(`/bom?orderId=${orderId}`);
    } catch (err) {
      setState((prev) => ({
        ...prev,
        error: err instanceof Error ? err.message : "Ошибка",
        isLoading: false,
      }));
    }
  }, [ensureAnonymousOrder, router, state.orderId, state.params]);

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
    sendChatMessage,
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
    cabinet_type: mapFurnitureCategoryToCabinetType(p.furniture_type?.category),
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

function mapFurnitureCategoryToCabinetType(category: string | null | undefined): string {
  // Нормализуем категории Vision OCR в наш внутренний enum (wall/base/...).
  // Если категоризация непонятна — оставляем пустым, чтобы пользователь выбрал вручную.
  switch (category) {
    case "навесной_шкаф":
      return "wall";
    case "напольный_шкаф":
    case "тумба":
      return "base";
    case "пенал":
      return "tall";
    case "ящик":
      return "drawer";
    default:
      return "";
  }
}

function normalizeFieldSources(
  raw: Record<string, FieldSource> | null | undefined
): Record<string, FieldSource> {
  const src = raw || {};

  // Схлопываем разные ключи в единый набор для UI.
  const result: Record<string, FieldSource> = {
    cabinet_type: src.cabinet_type ?? src.furniture_type ?? "default",
    width_mm: src.width_mm ?? "default",
    height_mm: src.height_mm ?? "default",
    depth_mm: src.depth_mm ?? "default",
    material: src.material ?? "default",
    thickness_mm: src.thickness_mm ?? "default",
    door_count: src.door_count ?? "default",
    drawer_count: src.drawer_count ?? "default",
    shelf_count: src.shelf_count ?? "default",
  };

  return result;
}

function toDialogueCurrentParams(params: Partial<OrderCreatorParams>) {
  // В JSON undefined пропускается, поэтому явно отправляем null для пропусков:
  // так ИИ понимает, что поле не заполнено.
  return {
    cabinet_type: params.cabinet_type ?? null,
    width_mm: params.width_mm ?? null,
    height_mm: params.height_mm ?? null,
    depth_mm: params.depth_mm ?? null,
    material: params.material ?? null,
    thickness_mm: params.thickness_mm ?? null,
    door_count: params.door_count ?? null,
    drawer_count: params.drawer_count ?? null,
    shelf_count: params.shelf_count ?? null,
  };
}

function parseAssistantParamUpdates(raw: string): {
  text: string;
  updates: Partial<OrderCreatorParams> | null;
} {
  const updates: Partial<OrderCreatorParams> = {};

  const blocks = raw.matchAll(/\[PARAM_UPDATE\]\s*([\s\S]*?)\s*\[\/PARAM_UPDATE\]/g);
  for (const match of blocks) {
    const jsonText = match[1];
    try {
      const patch = JSON.parse(jsonText) as Record<string, unknown>;
      Object.assign(updates, sanitizeParamUpdates(patch));
    } catch {
      // Игнорируем битый JSON, чтобы чат не ломался.
    }
  }

  const cleaned = raw.replace(/\[PARAM_UPDATE\][\s\S]*?\[\/PARAM_UPDATE\]/g, "").trim();

  return {
    text: cleaned,
    updates: Object.keys(updates).length ? updates : null,
  };
}

function sanitizeParamUpdates(patch: Record<string, unknown>): Partial<OrderCreatorParams> {
  const allowedCabinetTypes = new Set(["wall", "base", "base_sink", "drawer", "tall"]);

  const out: Partial<OrderCreatorParams> = {};

  const setNumber = (key: keyof OrderCreatorParams) => {
    const v = patch[key as string];
    if (v === null || v === undefined) return;
    const n = typeof v === "number" ? v : Number(v);
    if (!Number.isFinite(n)) return;
    // Для полей типа *_count и размеров — ожидаем целые.
    out[key] = Math.round(n) as never;
  };

  if (typeof patch.cabinet_type === "string" && allowedCabinetTypes.has(patch.cabinet_type)) {
    out.cabinet_type = patch.cabinet_type;
  }

  if (typeof patch.material === "string" && patch.material.trim()) {
    out.material = patch.material.trim();
  }

  setNumber("width_mm");
  setNumber("height_mm");
  setNumber("depth_mm");
  setNumber("thickness_mm");
  setNumber("door_count");
  setNumber("drawer_count");
  setNumber("shelf_count");

  return out;
}

function areRequiredParamsReady(params: Partial<OrderCreatorParams>): boolean {
  const typeOk = typeof params.cabinet_type === "string" && params.cabinet_type.trim().length > 0;

  const wOk = typeof params.width_mm === "number" && Number.isFinite(params.width_mm) && params.width_mm > 0;
  const hOk = typeof params.height_mm === "number" && Number.isFinite(params.height_mm) && params.height_mm > 0;
  const dOk = typeof params.depth_mm === "number" && Number.isFinite(params.depth_mm) && params.depth_mm > 0;

  return typeOk && wOk && hOk && dOk;
}
