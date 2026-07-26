'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { apiClient } from '@/lib/api-client'
import { track } from '@/lib/analytics'

interface LoginFormProps {
  onSent: (email: string, devMagicLink: string | null) => void
}

/**
 * Форма входа: только email. Честный copy — не подтверждаем существование
 * аккаунта. Backend всегда отвечает 200 (защита от перебора).
 */
export function LoginForm({ onSent }: LoginFormProps) {
  const [email, setEmail] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email || isLoading) return

    setIsLoading(true)
    setError(null)
    track({ name: 'magic_link_requested', properties: { auth_mode: 'login' } })

    try {
      const response = await apiClient.login({ email })
      onSent(email, response.dev_magic_link ?? null)
    } catch {
      // Backend отдаёт 200 даже для неизвестного email, поэтому реальная
      // ошибка здесь — сетевая. Сообщаем нейтрально, без утечки существования.
      setError('Не удалось отправить письмо. Проверьте соединение и попробуйте снова.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div className="flex flex-col gap-2">
        <Label htmlFor="login-email">Email</Label>
        <Input
          id="login-email"
          type="email"
          placeholder="director@mebel-pro.ru"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="email"
          aria-invalid={error ? true : undefined}
        />
      </div>

      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}

      <Button type="submit" className="w-full" disabled={isLoading}>
        {isLoading ? 'Отправляем…' : 'Получить ссылку для входа'}
      </Button>
    </form>
  )
}
