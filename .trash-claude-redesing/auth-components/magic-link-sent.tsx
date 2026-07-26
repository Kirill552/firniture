'use client'

import { Button } from '@/components/ui/button'
import { ArrowLeft, Mail } from 'lucide-react'
import type { AuthMode } from './auth-mode-switch'

interface MagicLinkSentProps {
  email: string
  mode: AuthMode
  devMagicLink: string | null
  onBack: () => void
}

/**
 * Экран «письмо отправлено». Для входа copy честный: не подтверждает
 * существование аккаунта. Для регистрации — прямое подтверждение.
 */
export function MagicLinkSent({ email, mode, devMagicLink, onBack }: MagicLinkSentProps) {
  const description =
    mode === 'login'
      ? 'Если аккаунт с таким адресом есть, ссылка придёт на почту.'
      : `Мы отправили ссылку для подтверждения на ${email}.`

  return (
    <div className="flex flex-col gap-6 text-center">
      <div className="flex flex-col items-center gap-4">
        <span className="flex h-14 w-14 items-center justify-center rounded-full bg-muted">
          <Mail className="h-6 w-6 text-foreground" aria-hidden />
        </span>
        <div className="flex flex-col gap-1.5">
          <h1 className="text-lg font-semibold text-foreground">Проверьте почту</h1>
          <p className="text-sm text-muted-foreground">{description}</p>
        </div>
      </div>

      {devMagicLink && (
        <div className="rounded-md border border-border bg-muted/50 p-3 text-left">
          <p className="mb-1 text-xs font-medium text-muted-foreground">
            DEV: magic-link
          </p>
          <a
            href={devMagicLink}
            className="break-all text-xs text-foreground underline underline-offset-2"
          >
            {devMagicLink}
          </a>
        </div>
      )}

      <div className="flex flex-col gap-2 text-left text-sm text-muted-foreground">
        <p>Ссылка действует 15 минут.</p>
        <p>Если письма нет — проверьте папку «Спам».</p>
      </div>

      <Button variant="outline" className="w-full" onClick={onBack}>
        <ArrowLeft className="h-4 w-4" aria-hidden />
        Изменить адрес
      </Button>
    </div>
  )
}
