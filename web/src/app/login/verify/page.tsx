'use client'

import { Suspense, useEffect, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Loader2, CheckCircle2, XCircle } from "lucide-react"
import { apiClient } from "@/lib/api-client"
import { setAuth } from "@/lib/auth"
import { resolveAuthReturnTarget } from "@/lib/auth-return"

type VerifyState = "loading" | "success" | "error"

function VerifyContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [state, setState] = useState<VerifyState>("loading")
  const [error, setError] = useState<string | null>(null)
  const [userName, setUserName] = useState<string>("")
  const [notice, setNotice] = useState<string | null>(null)

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

        // 1. Сохраняем сессию
        setAuth(response)
        setUserName(response.user.email)

        // 2. Пробуем привязать анонимный черновик
        let isClaimed = false
        let claimedOrderId: string | null = null
        try {
          const claimRes = await apiClient.claimGuestDraft()
          isClaimed = claimRes.claimed
          claimedOrderId = claimRes.order_id
        } catch (claimErr) {
          console.warn("Could not claim guest draft (likely missing cookie):", claimErr)
        }

        // 3. Считываем контекст входа из localStorage
        const isRegistering = typeof window !== "undefined" && localStorage.getItem("is_registering") === "true"
        const authEntry = typeof window !== "undefined" && localStorage.getItem("auth_entry")
        const queryEntry = searchParams.get("entry")
        const queryReturnTo = searchParams.get("returnTo")

        // Очищаем localStorage
        if (typeof window !== "undefined") {
          localStorage.removeItem("is_registering")
          localStorage.removeItem("auth_entry")
        }

        // 4. Проверяем, ожидали ли мы черновик
        const expectedDraft = authEntry === "save-draft" || queryEntry === "save-draft"

        if (expectedDraft && !isClaimed) {
          setState("success")
          setNotice("Локальный черновик не найден на этом устройстве.")
          // Честно сообщаем о переносе и ведем в заказы через 4 секунды
          setTimeout(() => {
            router.push("/orders")
          }, 4000)
        } else {
          setState("success")
          // Без лишних таймаутов переходим на нужную страницу
          const target = resolveAuthReturnTarget({
            isClaimed,
            claimedOrderId,
            isNewUser: isRegistering,
            returnTo: queryReturnTo,
          })
          router.push(target)
        }
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
    <div className="flex items-center justify-center min-h-[100dvh] bg-[#f3f6f8] px-4 py-8">
      <Card className="w-full max-w-[420px] bg-white border border-[#d7dde2] shadow-sm rounded-xl">
        {state === "loading" && (
          <CardHeader className="text-center p-6 space-y-4">
            <div className="flex justify-center">
              <Loader2 className="w-10 h-10 text-[#171a1d] animate-spin" />
            </div>
            <div className="space-y-1">
              <CardTitle className="text-base font-bold text-[#171a1d]">Проверяем ссылку...</CardTitle>
              <CardDescription className="text-xs text-[#66707a]">
                Подождите, мы подтверждаем ваш вход
              </CardDescription>
            </div>
          </CardHeader>
        )}

        {state === "success" && (
          <CardHeader className="text-center p-6 space-y-4">
            <div className="flex justify-center">
              <div className="w-12 h-12 rounded-full bg-[#c7ff00]/10 flex items-center justify-center">
                <CheckCircle2 className="w-6 h-6 text-[#171a1d]" />
              </div>
            </div>
            <div className="space-y-1">
              <CardTitle className="text-base font-bold text-[#171a1d]">Добро пожаловать!</CardTitle>
              <CardDescription className="text-xs text-[#66707a] leading-relaxed">
                Вы вошли как <span className="font-semibold">{userName}</span>
              </CardDescription>
            </div>
            <CardContent className="p-0 pt-2">
              <p className="text-xs text-[#66707a]">
                {notice || "Перенаправляем в личный кабинет..."}
              </p>
            </CardContent>
          </CardHeader>
        )}

        {state === "error" && (
          <CardHeader className="text-center p-6 space-y-4">
            <div className="flex justify-center">
              <div className="w-12 h-12 rounded-full bg-red-50 flex items-center justify-center">
                <XCircle className="w-6 h-6 text-red-600" />
              </div>
            </div>
            <div className="space-y-1">
              <CardTitle className="text-base font-bold text-[#171a1d]">Ошибка подтверждения</CardTitle>
              <CardDescription className="text-xs text-red-500 font-medium">
                {error || "Не удалось войти в систему"}
              </CardDescription>
            </div>
            <CardContent className="p-0 pt-2 space-y-4">
              <p className="text-xs text-[#66707a] leading-relaxed">
                Ссылка могла истечь или уже была использована. Запросите новую ссылку.
              </p>
              <Button
                className="w-full h-10 border border-[#d7dde2] bg-white hover:bg-[#f3f6f8] text-[#171a1d] font-semibold active:scale-[0.98] transition-all duration-150 rounded-lg cursor-pointer text-xs"
                onClick={() => router.push("/login")}
              >
                Вернуться на страницу входа
              </Button>
            </CardContent>
          </CardHeader>
        )}
      </Card>
    </div>
  )
}

function LoadingFallback() {
  return (
    <div className="flex items-center justify-center min-h-[100dvh] bg-[#f3f6f8]">
      <div className="text-sm text-[#66707a]">Загрузка...</div>
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
