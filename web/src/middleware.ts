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
  '/welcome', // Онбординг для новых пользователей
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

  // Редиректы удалённых страниц → /orders
  if (['/dashboard', '/history', '/hardware'].includes(pathname)) {
    return NextResponse.redirect(new URL('/orders', request.url))
  }

  // Старый вход → новый с табом
  if (pathname === '/orders/new') {
    return NextResponse.redirect(new URL('/new?tab=manual', request.url))
  }

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
