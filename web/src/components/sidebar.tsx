"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"
import { FileText, Wrench, Link2, Settings, Plus } from "lucide-react"

const sidebarNavItems = [
  {
    title: "Заказы",
    url: "/orders",
    icon: FileText,
  },
  {
    title: "Файлы для станка",
    url: "/cam",
    icon: Wrench,
  },
  {
    title: "Интеграции",
    url: "/integrations",
    icon: Link2,
  },
  {
    title: "Настройки",
    url: "/settings",
    icon: Settings,
  },
]

export function AppSidebar() {
  const pathname = usePathname()

  return (
    <Sidebar className="pt-14">
      <SidebarHeader className="border-b border-sidebar-border">
        <Link href="/orders" className="flex items-center gap-3 px-3 py-4">
          {/* Логотип — стилизованная буква А */}
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold text-lg">
            А
          </div>
          <div className="flex flex-col">
            <span className="font-semibold text-sm">АвтоРаскрой</span>
            <span className="text-xs text-muted-foreground">Умный раскрой</span>
          </div>
        </Link>
        {/* CTA: Новый заказ */}
        <div className="px-3 pb-4">
          <Button asChild className="w-full">
            <Link href="/new">
              <Plus className="mr-2 h-4 w-4" />
              Новый заказ
            </Link>
          </Button>
        </div>
      </SidebarHeader>
      <SidebarContent className="px-2 py-4">
        <SidebarGroup>
          <SidebarMenu>
            {sidebarNavItems.map((item) => {
              const IconComponent = item.icon
              const isActive = pathname === item.url || pathname.startsWith(item.url + '/')

              return (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    asChild
                    className={cn(
                      "transition-colors",
                      isActive && "bg-sidebar-accent text-sidebar-accent-foreground"
                    )}
                  >
                    <Link href={item.url}>
                      <IconComponent className={cn(
                        "h-4 w-4",
                        isActive ? "text-primary" : "text-muted-foreground"
                      )} />
                      <span className={cn(
                        isActive && "font-medium"
                      )}>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              )
            })}
          </SidebarMenu>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  )
}
