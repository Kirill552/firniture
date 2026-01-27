"use client";

import { useState } from "react";
import type {
  ExtractedFurnitureParams,
  ImageExtractResponse,
  ImageMimeType
} from "@/types/api";

interface UseVisionOCRReturn {
  analyze: (file: File) => Promise<ImageExtractResponse | null>;
  isLoading: boolean;
  error: string | null;
  result: ImageExtractResponse | null;
}

export function useVisionOCR(): UseVisionOCRReturn {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ImageExtractResponse | null>(null);

  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = (reader.result as string).split(",")[1];
        resolve(base64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  };

  const analyze = async (file: File): Promise<ImageExtractResponse | null> => {
    setIsLoading(true);
    setError(null);

    try {
      const base64 = await fileToBase64(file);

      const response = await fetch("/api/v1/spec/extract-from-image", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          image_base64: base64,
          image_mime_type: file.type as ImageMimeType,
          language_hint: "ru",
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Ошибка распознавания");
      }

      const data: ImageExtractResponse = await response.json();
      setResult(data);
      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Неизвестная ошибка";
      setError(message);
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  return { analyze, isLoading, error, result };
}

// Re-export types for convenience
export type { ExtractedFurnitureParams, ImageExtractResponse };
