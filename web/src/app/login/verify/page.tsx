'use client'

import { Suspense, useEffect, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Loader2, CheckCircle2, XCircle } from "lucide-react"
import { apiClient } from "@/lib/api-client"
import { setAuth } from "@/lib/auth"

type VerifyState = "loading" | "success" | "error"

function VerifyContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [state, setState] = useState<VerifyState>("loading")
  const [error, setError] = useState<string | null>(null)
  const [userName, setUserName] = useState<string>("")

  useEffect(() => {
    const token = searchParams.get("token")

    if (!token) {
      setState("error")
      setError("Токен не найден в ссылке")
      return
    }

    const verifyToken = async () => {
      try {
        const response = await apiClient.verify({ token })

        // Сохраняем токен и данные пользователя
        setAuth(response)
        setUserName(response.user.email)
        setState("success")

        // Редирект на orders через 2 секунды
        setTimeout(() => {
          router.push("/orders")
        }, 2000)
      } catch (err: unknown) {
        setState("error")
        if (err && typeof err === 'object' && 'detail' in err) {
          setError(String(err.detail))
        } else {
          setError("Ссылка недействительна или истекла")
        }
      }
    }

    verifyToken()
  }, [searchParams, router])

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-950">
      <Card className="w-[420px]">
        {state === "loading" && (
          <>
            <CardHeader className="text-center">
              <div className="flex justify-center mb-4">
                <Loader2 className="w-12 h-12 text-primary animate-spin" />
              </div>
              <CardTitle>Проверяем ссылку...</CardTitle>
              <CardDescription>
                Подождите, мы проверяем вашу ссылку для входа
              </CardDescription>
            </CardHeader>
          </>
        )}

        {state === "success" && (
          <>
            <CardHeader className="text-center">
              <div className="flex justify-center mb-4">
                <div className="w-16 h-16 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                  <CheckCircle2 className="w-8 h-8 text-green-600 dark:text-green-400" />
                </div>
              </div>
              <CardTitle>Добро пожаловать!</CardTitle>
              <CardDescription>
                Вы успешно вошли как {userName}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-center text-sm text-muted-foreground">
                Перенаправляем в личный кабинет...
              </p>
            </CardContent>
          </>
        )}

        {state === "error" && (
          <>
            <CardHeader className="text-center">
              <div className="flex justify-center mb-4">
                <div className="w-16 h-16 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
                  <XCircle className="w-8 h-8 text-red-600 dark:text-red-400" />
                </div>
              </div>
              <CardTitle>Ошибка входа</CardTitle>
              <CardDescription>
                {error || "Не удалось войти в систему"}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-center text-sm text-muted-foreground">
                Ссылка могла истечь или уже была использована.
                Запросите новую ссылку для входа.
              </p>
              <Button
                className="w-full"
                onClick={() => router.push("/login")}
              >
                Вернуться на страницу входа
              </Button>
            </CardContent>
          </>
        )}
      </Card>
    </div>
  )
}

function LoadingFallback() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-950">
      <Card className="w-[420px]">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <Loader2 className="w-12 h-12 text-primary animate-spin" />
          </div>
          <CardTitle>Загрузка...</CardTitle>
        </CardHeader>
      </Card>
    </div>
  )
}

export default function VerifyPage() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <VerifyContent />
    </Suspense>
  )
}
