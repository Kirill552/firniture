'use client'

import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { getUser, getToken, logout as authLogout, AuthUser } from '@/lib/auth'

interface AuthContextType {
  user: AuthUser | null
  isLoading: boolean
  isAuthenticated: boolean
  logout: () => void
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  isLoading: true,
  isAuthenticated: false,
  logout: () => {},
})

/**
 * Публичные пути, не требующие авторизации
 */
const publicPaths = ['/', '/login', '/login/verify', '/signup', '/welcome']

function isPublicPath(pathname: string): boolean {
  return publicPaths.some(path => {
    if (path === pathname) return true
    if (path === '/login' && pathname.startsWith('/login/')) return true
    return false
  })
}

/**
 * Проверяет, нужен ли онбординг
 */
function needsOnboarding(): boolean {
  if (typeof window === 'undefined') return false
  return localStorage.getItem('onboarding_completed') !== 'true'
}

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const router = useRouter()
  const pathname = usePathname()
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Проверяем авторизацию при загрузке
    const token = getToken()
    const storedUser = getUser()

    if (token && storedUser) {
      setUser(storedUser)
    }

    setIsLoading(false)
  }, [])

  useEffect(() => {
    // Редирект неавторизованных с защищённых страниц
    if (!isLoading && !user && !isPublicPath(pathname)) {
      router.push('/login')
      return
    }

    // Редирект на онбординг для новых пользователей
    // (только если залогинены и не на /welcome)
    if (!isLoading && user && pathname !== '/welcome' && needsOnboarding()) {
      router.push('/welcome')
    }
  }, [isLoading, user, pathname, router])

  const logout = () => {
    authLogout()
    setUser(null)
    router.push('/login')
  }

  // Показываем loading пока проверяем авторизацию
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  // Для защищённых страниц без авторизации — показываем loading (редирект в useEffect)
  if (!user && !isPublicPath(pathname)) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
