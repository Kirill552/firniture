/**
 * Модуль аутентификации для Magic Link
 *
 * Хранение токена: localStorage (для MVP)
 * В production рекомендуется httpOnly cookie
 */

const TOKEN_KEY = 'auth_token'
const USER_KEY = 'auth_user'

export interface AuthUser {
  id: string
  email: string
  is_owner: boolean
  factory: {
    id: string
    name: string
  }
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: AuthUser
}

/**
 * Сохранить токен и пользователя после успешной верификации
 */
export function setAuth(data: TokenResponse): void {
  if (typeof window === 'undefined') return

  localStorage.setItem(TOKEN_KEY, data.access_token)
  localStorage.setItem(USER_KEY, JSON.stringify(data.user))
}

/**
 * Получить токен авторизации
 */
export function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(TOKEN_KEY)
}

/**
 * Получить текущего пользователя
 */
export function getUser(): AuthUser | null {
  if (typeof window === 'undefined') return null

  const userJson = localStorage.getItem(USER_KEY)
  if (!userJson) return null

  try {
    return JSON.parse(userJson)
  } catch {
    return null
  }
}

/**
 * Проверить авторизован ли пользователь
 */
export function isAuthenticated(): boolean {
  return !!getToken()
}

/**
 * Выйти из системы
 */
export function logout(): void {
  if (typeof window === 'undefined') return

  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

/**
 * Получить заголовок Authorization
 */
export function getAuthHeader(): Record<string, string> {
  const token = getToken()
  if (!token) return {}

  return {
    Authorization: `Bearer ${token}`
  }
}
