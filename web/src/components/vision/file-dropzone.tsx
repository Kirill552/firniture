"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileImage, Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface FileDropzoneProps {
  onFileSelect: (file: File) => void;
  isLoading?: boolean;
  accept?: Record<string, string[]>;
  maxSize?: number;
}

export function FileDropzone({
  onFileSelect,
  isLoading = false,
  accept = { "image/*": [".jpeg", ".jpg", ".png", ".webp"], "application/pdf": [".pdf"] },
  maxSize = 10 * 1024 * 1024, // 10MB
}: FileDropzoneProps) {
  const [preview, setPreview] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      const file = acceptedFiles[0];
      if (!file) return;

      setFileName(file.name);

      // Превью для изображений
      if (file.type.startsWith("image/")) {
        const reader = new FileReader();
        reader.onload = () => setPreview(reader.result as string);
        reader.readAsDataURL(file);
      } else {
        setPreview(null);
      }

      onFileSelect(file);
    },
    [onFileSelect]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept,
    maxFiles: 1,
    maxSize,
    disabled: isLoading,
  });

  const clearFile = () => {
    setPreview(null);
    setFileName(null);
  };

  return (
    <div
      {...getRootProps()}
      className={cn(
        "relative cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition-all",
        isDragActive && "border-primary bg-primary/5",
        isLoading && "pointer-events-none opacity-60",
        !isDragActive && "border-muted-foreground/25 hover:border-primary/50"
      )}
    >
      <input {...getInputProps()} />

      {isLoading ? (
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-12 w-12 animate-spin text-primary" />
          <div>
            <p className="font-medium">Распознаём эскиз...</p>
            <p className="text-sm text-muted-foreground">
              Обычно это занимает 5-10 секунд
            </p>
          </div>
        </div>
      ) : preview ? (
        <div className="flex flex-col items-center gap-4">
          <div className="relative">
            <img
              src={preview}
              alt="Превью"
              className="max-h-48 rounded-lg object-contain"
            />
            <Button
              size="icon"
              variant="destructive"
              className="absolute -right-2 -top-2 h-6 w-6"
              onClick={(e) => {
                e.stopPropagation();
                clearFile();
              }}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
          <p className="text-sm text-muted-foreground">{fileName}</p>
        </div>
      ) : fileName ? (
        <div className="flex flex-col items-center gap-4">
          <div className="rounded-full bg-primary/10 p-4">
             <FileImage className="h-8 w-8 text-primary" />
          </div>
           <div className="relative">
             <p className="text-lg font-medium">{fileName}</p>
              <Button
                size="icon"
                variant="destructive"
                className="absolute -right-8 -top-1 h-6 w-6"
                onClick={(e) => {
                  e.stopPropagation();
                  clearFile();
                }}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-4">
          <div className="rounded-full bg-primary/10 p-4">
            <Upload className="h-8 w-8 text-primary" />
          </div>
          <div>
            <p className="text-lg font-medium">
              {isDragActive ? "Отпустите файл" : "Загрузите фото эскиза"}
            </p>
            <p className="text-sm text-muted-foreground">
              или перетащите файл сюда
            </p>
          </div>
          <p className="text-xs text-muted-foreground">
            JPG, PNG, WebP, PDF до 10 МБ
          </p>
        </div>
      )}
    </div>
  );
}
