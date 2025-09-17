'use client'

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export default function SettingsPage() {
  return (
    <div className="p-6 w-full max-w-2xl mx-auto">
      <Card>
        <CardHeader>
          <CardTitle>Настройки профиля</CardTitle>
          <CardDescription>Управление информацией вашего аккаунта.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="name">Имя</Label>
            <Input id="name" defaultValue="Технолог" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" defaultValue="m@example.com" readOnly />
          </div>
          
          <CardTitle>Смена пароля</CardTitle>
          
          <div className="space-y-2">
            <Label htmlFor="current-password">Текущий пароль</Label>
            <Input id="current-password" type="password" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="new-password">Новый пароль</Label>
            <Input id="new-password" type="password" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="confirm-password">Подтвердите новый пароль</Label>
            <Input id="confirm-password" type="password" />
          </div>

          <Button>Сохранить изменения</Button>
        </CardContent>
      </Card>
    </div>
  )
}