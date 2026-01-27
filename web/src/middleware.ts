import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

/**
 * Публичные пути, не требующие авторизации
 */
const publicPaths = [
  '/',
  '/login',
  '/login/verify',
  '/signup',  // legacy, редирект на /login
  '/new',     // Vision-first freemium (без авторизации)
]

/**
 * Проверяет, является ли путь публичным
 */
function isPublicPath(pathname: string): boolean {
  return publicPaths.some(path => {
    if (path === pathname) return true
    // Поддержка вложенных путей для /login/* и /new/*
    if (path === '/login' && pathname.startsWith('/login/')) return true
    if (path === '/new' && pathname.startsWith('/new/')) return true
    return false
  })
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Пропускаем статику и API
  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/api') ||
    pathname.includes('.') // файлы с расширением (favicon.ico, etc)
  ) {
    return NextResponse.next()
  }

  // Публичные пути доступны всем
  if (isPublicPath(pathname)) {
    return NextResponse.next()
  }

  // Для защищённых путей проверяем токен в cookie или localStorage
  // Примечание: middleware работает на edge, localStorage недоступен
  // Для MVP используем клиентскую проверку в layout
  // Здесь только базовая защита через cookie (если добавим позже)

  // Пока пропускаем все запросы — проверка будет на клиенте
  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
}
