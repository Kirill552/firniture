'use client'

import { usePathname } from 'next/navigation'
import { AppBar } from "@/components/app-bar"
import { AppSidebar } from "@/components/sidebar"
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar"
import { ReactNode } from 'react'
import { Breadcrumbs } from "@/components/breadcrumbs"
import { AuthProvider } from "@/components/auth-provider"

interface AuthLayoutProps {
  children: ReactNode
}

export default function AuthLayout({ children }: AuthLayoutProps) {
  const pathname = usePathname()

  const publicPaths = ['/', '/login', '/login/verify', '/pricing', '/signup', '/welcome']

  const isPublic = publicPaths.some(path => {
    if (path === pathname) return true
    if (path === '/login' && pathname.startsWith('/login/')) return true
    return false
  })

  // Публичные страницы без AuthProvider (но /welcome требует проверку онбординга)
  if (isPublic) {
    return <>{children}</>
  }

  // Защищённые страницы с AuthProvider
  return (
    <AuthProvider>
      <AuthenticatedLayout>{children}</AuthenticatedLayout>
    </AuthProvider>
  )
}

function AuthenticatedLayout({ children }: { children: ReactNode }) {

  return (
    <SidebarProvider>
      <div className="min-h-screen w-full">
        <AppBar />
        <div className="grid min-h-[calc(100vh-3.5rem)] w-full grid-cols-[16rem_1fr]">
          <AppSidebar />
          <SidebarInset className="w-full min-w-0">
            <div className="flex h-full w-full flex-col">
              <div className="px-8 pt-6 pb-4">
                <Breadcrumbs />
              </div>
              <main className="flex-1 px-8 pb-10">
                <div className="mx-auto w-full max-w-7xl space-y-8">
                  {children}
                </div>
              </main>
            </div>
          </SidebarInset>
        </div>
      </div>
    </SidebarProvider>
  )
}
