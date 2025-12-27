'use client'

import { useRouter, useSearchParams } from 'next/navigation'
import { useState } from 'react'
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Upload, FileText } from "lucide-react"
import { FileDropzone } from '@/components/upload/file-dropzone'

export default function TzUploadPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const orderId = searchParams.get('orderId')

  const [text, setText] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [isLoading, setIsLoading] = useState(false)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files))
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!orderId) return

    setIsLoading(true)
    // Mock upload
    await new Promise(resolve => setTimeout(resolve, 1000))
    // In real, upload files to storage, send to API with text
    router.push(`/orders/new/dialogue?orderId=${orderId}`)
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900 p-4">
      <Card className="w-full max-w-2xl">
        <CardHeader>
          <CardTitle>Загрузка технического задания</CardTitle>
          <CardDescription>Введите описание или загрузите файлы (эскиз, фото, текст ТЗ).</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="text">Описание ТЗ</Label>
              <Textarea
                id="text"
                placeholder="Опишите изделие, размеры, материалы..."
                value={text}
                onChange={(e) => setText(e.target.value)}
                className="min-h-[120px]"
              />
            </div>
            <div className="space-y-3">
              <Label>Загрузить файлы</Label>
              <FileDropzone
                onFiles={(newFiles) => setFiles(prev => [...prev, ...newFiles])}
                onReject={(reasons) => console.warn('reject', reasons)}
                accept={['.png','.jpg','.jpeg','.pdf','.txt','.doc','.docx']}
                maxFiles={8}
                description="Поддерживаются изображения, PDF и текстовые документы"
              />
              {files.length > 0 && (
                <ul className="text-xs text-muted-foreground space-y-1 max-h-32 overflow-auto border rounded p-2">
                  {files.map(f => <li key={f.name}>{f.name} • {Math.round(f.size/1024)} KB</li>)}
                </ul>
              )}
            </div>
            <Button type="submit" className="w-full" disabled={isLoading || !orderId}>
              {isLoading ? "Обработка..." : "Продолжить к диалогу с ИИ"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}