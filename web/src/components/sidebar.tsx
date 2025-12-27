import * as React from "react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarSeparator,
} from "@/components/ui/sidebar"
import { Home, FileText, Package, Database, Zap, Users, History, Shield, Settings } from "lucide-react"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

const sidebarNavItems = [
  { title: "Главная (Дашборд)", url: "/dashboard", icon: Home },
  { title: "Заказы", url: "/orders", icon: FileText },
  { title: "Спецификация (BOM)", url: "/bom", icon: Package },
  { title: "Фурнитура (RAG-подбор)", url: "/hardware", icon: Database },
  { title: "CAM (DXF/G-code)", url: "/cam", icon: Zap },
  { title: "Интеграции (1С)", url: "/integrations", icon: Users },
  { title: "История заказов", url: "/history", icon: History },
  { title: "Настройки", url: "/settings", icon: Settings },
]

export function AppSidebar() {
  return (
    <Sidebar>
      <SidebarHeader>
        <Button variant="ghost" className="w-full justify-start gap-2">
          <Shield className="h-4 w-4" />
          <span className="font-semibold">Мебель-ИИ</span>
        </Button>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarMenu>
            {sidebarNavItems.map((item) => {
              const IconComponent = item.icon
              return (
                <SidebarMenuItem key={item.title}>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <SidebarMenuButton asChild>
                        <Link href={item.url}>
                          <IconComponent className="mr-2 h-4 w-4" />
                          <span>{item.title}</span>
                        </Link>
                      </SidebarMenuButton>
                    </TooltipTrigger>
                    <TooltipContent side="right" sideOffset={8}>
                      {item.title}
                    </TooltipContent>
                  </Tooltip>
                </SidebarMenuItem>
              )
            })}
          </SidebarMenu>
        </SidebarGroup>
        <SidebarSeparator />
      </SidebarContent>
    </Sidebar>
  )
}