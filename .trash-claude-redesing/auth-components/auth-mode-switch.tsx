'use client'

import { motion, useReducedMotion } from 'framer-motion'

export type AuthMode = 'login' | 'register'

interface AuthModeSwitchProps {
  mode: AuthMode
  onChange: (mode: AuthMode) => void
}

const OPTIONS: { value: AuthMode; label: string }[] = [
  { value: 'login', label: 'Войти' },
  { value: 'register', label: 'Создать аккаунт' },
]

/**
 * Сегментированный переключатель режимов. Всегда виден: формы не угадывают,
 * есть ли email, пользователь сам выбирает вход или регистрацию.
 * Индикатор скользит между сегментами (spring), фон — theme tokens.
 */
export function AuthModeSwitch({ mode, onChange }: AuthModeSwitchProps) {
  const reduce = useReducedMotion()

  return (
    <div
      role="tablist"
      aria-label="Режим входа"
      className="relative grid grid-cols-2 gap-1 rounded-lg bg-muted p-1"
    >
      {OPTIONS.map((option) => {
        const active = option.value === mode
        return (
          <button
            key={option.value}
            role="tab"
            type="button"
            aria-selected={active}
            onClick={() => onChange(option.value)}
            className="relative z-10 rounded-md px-3 py-2 text-sm font-medium transition-colors data-[active=false]:text-muted-foreground data-[active=true]:text-foreground"
            data-active={active}
          >
            {active && (
              <motion.span
                layoutId="auth-mode-indicator"
                className="absolute inset-0 -z-10 rounded-md bg-card shadow-sm"
                transition={
                  reduce
                    ? { duration: 0 }
                    : { type: 'spring', stiffness: 500, damping: 40 }
                }
              />
            )}
            {option.label}
          </button>
        )
      })}
    </div>
  )
}
