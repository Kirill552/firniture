"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { useFeatureFlags } from "@/features/mvp"
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
  const { machineFeaturesEnabled } = useFeatureFlags()
  
  const filteredNavItems = sidebarNavItems.filter(
    (item) => item.url !== "/cam" || machineFeaturesEnabled
  )

  return (
    <Sidebar className="pt-14">
      <SidebarHeader className="border-b border-[#d7dde2] bg-white">
        <Link href="/orders" className="flex items-center gap-3 px-3 py-4 select-none">
          <span className="relative flex h-8 w-8 items-center justify-center border border-[#d7dde2] bg-white rounded-lg shrink-0">
            <span className="text-[14px] font-extrabold tracking-[-1px] text-[#171a1d]">АР</span>
            <span className="absolute -right-[2px] -top-[2px] h-2 w-2 rounded-full bg-[#c7ff00]" />
          </span>
          <span className="flex flex-col leading-none">
            <span className="text-[14px] font-bold tracking-[-0.6px] text-[#171a1d]">АвтоРаскрой</span>
            <span className="font-mono mt-0.5 text-[8.5px] uppercase tracking-[1.5px] text-[#66707a]">
              обмер · спецификация
            </span>
          </span>
        </Link>
        {/* CTA: Новый заказ */}
        <div className="px-3 pb-4">
          <Button asChild className="w-full bg-[#c7ff00] hover:bg-[#aee600] text-[#171a1d] font-semibold border-0 active:scale-[0.98] transition-all duration-150 cursor-pointer shadow-sm">
            <Link href="/new">
              <Plus className="mr-1.5 h-4 w-4 text-[#171a1d]" />
              Новый заказ
            </Link>
          </Button>
        </div>
      </SidebarHeader>
      <SidebarContent className="px-2 py-4">
        <SidebarGroup>
          <SidebarMenu>
            {filteredNavItems.map((item) => {
              const IconComponent = item.icon
              const isActive = pathname === item.url || pathname.startsWith(item.url + '/')

              return (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    asChild
                    className={cn(
                      "transition-all duration-150 relative pl-6",
                      isActive 
                        ? "bg-[#171a1d] text-white hover:bg-[#171a1d] hover:text-white" 
                        : "text-[#66707a] hover:text-[#171a1d] hover:bg-[#f3f6f8]"
                    )}
                  >
                    <Link href={item.url}>
                      {isActive && (
                        <span className="absolute left-2.5 top-1/2 -translate-y-1/2 w-1 h-3 rounded-full bg-[#c7ff00]" />
                      )}
                      <IconComponent className={cn(
                        "h-4 w-4",
                        isActive ? "text-[#c7ff00]" : "text-[#66707a]"
                      )} />
                      <span className={cn(
                        isActive && "font-bold"
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
