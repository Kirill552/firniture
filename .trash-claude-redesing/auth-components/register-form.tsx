'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { apiClient, APIClientError } from '@/lib/api-client'
import { track } from '@/lib/analytics'

interface RegisterFormProps {
  onSent: (email: string, devMagicLink: string | null) => void
  onSwitchToLogin: () => void
}

/**
 * Форма регистрации: email + название фабрики. При 409 (email занят)
 * честно ведём в режим входа, а не притворяемся, что письмо отправлено.
 */
export function RegisterForm({ onSent, onSwitchToLogin }: RegisterFormProps) {
  const [email, setEmail] = useState('')
  const [factoryName, setFactoryName] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [emailTaken, setEmailTaken] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email || !factoryName || isLoading) return

    setIsLoading(true)
    setError(null)
    setEmailTaken(false)
    track({ name: 'magic_link_requested', properties: { auth_mode: 'register' } })

    try {
      const response = await apiClient.register({ email, factory_name: factoryName })
      onSent(email, response.dev_magic_link ?? null)
    } catch (err) {
      if (err instanceof APIClientError && err.status === 409) {
        setEmailTaken(true)
        setError('Аккаунт уже есть — войдите.')
      } else {
        setError('Не удалось зарегистрироваться. Попробуйте позже.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div className="flex flex-col gap-2">
        <Label htmlFor="register-email">Email</Label>
        <Input
          id="register-email"
          type="email"
          placeholder="director@mebel-pro.ru"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="email"
          aria-invalid={error ? true : undefined}
        />
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="register-factory">Название фабрики</Label>
        <Input
          id="register-factory"
          type="text"
          placeholder="ООО «Мебель-Про»"
          required
          value={factoryName}
          onChange={(e) => setFactoryName(e.target.value)}
          autoComplete="organization"
        />
      </div>

      {error && (
        <div role="alert" className="flex flex-col gap-2 text-sm text-destructive">
          <span>{error}</span>
          {emailTaken && (
            <button
              type="button"
              onClick={onSwitchToLogin}
              className="self-start font-medium text-foreground underline underline-offset-4 hover:no-underline"
            >
              Перейти ко входу
            </button>
          )}
        </div>
      )}

      <Button type="submit" className="w-full" disabled={isLoading}>
        {isLoading ? 'Создаём аккаунт…' : 'Создать аккаунт'}
      </Button>
    </form>
  )
}
