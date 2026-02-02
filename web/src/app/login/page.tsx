'use client'

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ArrowLeft, Mail, Building2, CheckCircle2 } from "lucide-react"
import { apiClient } from "@/lib/api-client"

type AuthStep = "enter-email" | "check-email" | "register"

export default function LoginPage() {
  const [step, setStep] = useState<AuthStep>("enter-email")
  const [email, setEmail] = useState("")
  const [factoryName, setFactoryName] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isNewUser, setIsNewUser] = useState(false)
  const [devMagicLink, setDevMagicLink] = useState<string | null>(null)

  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email) return

    setIsLoading(true)
    setError(null)

    try {
      // Пробуем отправить magic link
      const response = await apiClient.login({ email })
      setIsNewUser(false)
      setDevMagicLink(response.dev_magic_link || null)
      setStep("check-email")
    } catch (err: unknown) {
      // Если пользователь не найден — предлагаем регистрацию
      if (err && typeof err === 'object' && 'status' in err && err.status === 404) {
        setIsNewUser(true)
        setStep("register")
      } else {
        // Для других ошибок или успеха показываем "проверьте почту"
        // (API всегда возвращает 200 для защиты от перебора)
        setStep("check-email")
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email || !factoryName) return

    setIsLoading(true)
    setError(null)

    try {
      const response = await apiClient.register({ email, factory_name: factoryName })
      setIsNewUser(true)
      setDevMagicLink(response.dev_magic_link || null)
      setStep("check-email")
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'detail' in err) {
        setError(String(err.detail))
      } else {
        setError("Не удалось зарегистрироваться. Попробуйте позже.")
      }
    } finally {
      setIsLoading(false)
    }
  }

  const resetFlow = () => {
    setStep("enter-email")
    setError(null)
    setDevMagicLink(null)
  }

  const formVariants = {
    initial: { opacity: 0, x: 300 },
    animate: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: -300 },
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-950">
      <Card className="w-[420px] overflow-hidden relative">
        <AnimatePresence initial={false} mode="wait">
          <motion.div
            key={step}
            variants={formVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={{ type: "tween", duration: 0.35, ease: "easeInOut" }}
          >
            {step === "enter-email" && (
              <form onSubmit={handleEmailSubmit}>
                <CardHeader>
                  <CardTitle>Вход в АвтоРаскрой</CardTitle>
                  <CardDescription>
                    Введите email — мы отправим ссылку для входа
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <Input
                      id="email"
                      type="email"
                      placeholder="director@mebel-pro.ru"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      autoComplete="email"
                    />
                  </div>
                  {error && (
                    <p className="text-sm text-red-500">{error}</p>
                  )}
                  <Button type="submit" className="w-full" disabled={isLoading}>
                    {isLoading ? "Отправка..." : "Продолжить"}
                  </Button>
                  <p className="text-xs text-center text-muted-foreground">
                    Нет аккаунта?{" "}
                    <button
                      type="button"
                      onClick={() => setStep("register")}
                      className="text-primary hover:underline"
                    >
                      Зарегистрируйте фабрику
                    </button>
                  </p>
                </CardContent>
              </form>
            )}

            {step === "check-email" && (
              <div>
                <CardHeader>
                  <div className="flex justify-center mb-4">
                    <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
                      <Mail className="w-8 h-8 text-primary" />
                    </div>
                  </div>
                  <CardTitle className="text-center">Проверьте почту</CardTitle>
                  <CardDescription className="text-center">
                    {isNewUser
                      ? `Мы отправили ссылку для завершения регистрации на ${email}`
                      : `Мы отправили ссылку для входа на ${email}`
                    }
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {devMagicLink && (
                    <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
                      <p className="text-xs font-medium text-yellow-800 dark:text-yellow-200 mb-2">
                        🔧 DEV MODE — Magic Link:
                      </p>
                      <a
                        href={devMagicLink}
                        className="text-sm text-blue-600 dark:text-blue-400 hover:underline break-all"
                      >
                        {devMagicLink}
                      </a>
                    </div>
                  )}
                  <div className="bg-muted/50 rounded-lg p-4 text-sm text-muted-foreground">
                    <p className="flex items-start gap-2">
                      <CheckCircle2 className="w-4 h-4 mt-0.5 text-green-500 shrink-0" />
                      Ссылка действительна 15 минут
                    </p>
                    <p className="flex items-start gap-2 mt-2">
                      <CheckCircle2 className="w-4 h-4 mt-0.5 text-green-500 shrink-0" />
                      Проверьте папку «Спам» если письма нет
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={resetFlow}
                  >
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Изменить email
                  </Button>
                </CardContent>
              </div>
            )}

            {step === "register" && (
              <form onSubmit={handleRegister}>
                <CardHeader>
                  <button
                    type="button"
                    onClick={resetFlow}
                    className="flex items-center text-sm text-muted-foreground hover:text-primary transition-colors mb-2"
                  >
                    <ArrowLeft className="w-4 h-4 mr-1" />
                    Назад
                  </button>
                  <CardTitle>Регистрация фабрики</CardTitle>
                  <CardDescription>
                    Создайте аккаунт для вашей мебельной фабрики
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="reg-email">Email</Label>
                    <Input
                      id="reg-email"
                      type="email"
                      placeholder="director@mebel-pro.ru"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      autoComplete="email"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="factory-name">Название фабрики</Label>
                    <div className="relative">
                      <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input
                        id="factory-name"
                        type="text"
                        placeholder="ООО Мебель-Про"
                        required
                        value={factoryName}
                        onChange={(e) => setFactoryName(e.target.value)}
                        className="pl-10"
                      />
                    </div>
                  </div>
                  {error && (
                    <p className="text-sm text-red-500">{error}</p>
                  )}
                  <Button type="submit" className="w-full" disabled={isLoading}>
                    {isLoading ? "Регистрация..." : "Зарегистрироваться"}
                  </Button>
                  <p className="text-xs text-center text-muted-foreground">
                    Нажимая кнопку, вы соглашаетесь с условиями использования
                  </p>
                </CardContent>
              </form>
            )}
          </motion.div>
        </AnimatePresence>
      </Card>
    </div>
  )
}
