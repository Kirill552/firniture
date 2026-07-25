'use client'

import { useState, useEffect, Suspense } from "react"
import { useSearchParams } from "next/navigation"
import { motion, AnimatePresence } from "framer-motion"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ArrowLeft, Mail, Building2, CheckCircle2 } from "lucide-react"
import { apiClient } from "@/lib/api-client"

function LoginFormInner() {
  const searchParams = useSearchParams()
  const modeParam = searchParams.get("mode")
  const entryParam = searchParams.get("entry")

  // Default mode is register if entry=save-draft or mode=register
  const defaultMode = (entryParam === "save-draft" || modeParam === "register") ? "register" : "login"

  const [activeMode, setActiveMode] = useState<"login" | "register">("login")
  const [step, setStep] = useState<"form" | "check-email">("form")
  const [email, setEmail] = useState("")
  const [factoryName, setFactoryName] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isNewUser, setIsNewUser] = useState(false)
  const [devMagicLink, setDevMagicLink] = useState<string | null>(null)

  useEffect(() => {
    setActiveMode(defaultMode)
  }, [defaultMode])

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email) return

    setIsLoading(true)
    setError(null)

    if (typeof window !== "undefined") {
      localStorage.setItem("auth_entry", entryParam || "")
      localStorage.setItem("is_registering", "false")
    }
    try {
      const returnToParam = searchParams.get("returnTo") || undefined
      const response = await apiClient.login({
        email,
        return_to: returnToParam,
        entry: entryParam || undefined,
      })
      setDevMagicLink(response.dev_magic_link || null)
    } catch (err: unknown) {
      // Ignore errors for login email lookup to prevent enumeration
      // but log it for dev visibility if it's a network issue
      console.warn("Login endpoint returned error (ignoring for security):", err)
    } finally {
      setIsNewUser(false)
      setStep("check-email")
      setIsLoading(false)
    }
  }

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email || !factoryName) return

    setIsLoading(true)
    setError(null)

    if (typeof window !== "undefined") {
      localStorage.setItem("auth_entry", entryParam || "")
      localStorage.setItem("is_registering", "true")
    }
    try {
      const returnToParam = searchParams.get("returnTo") || undefined
      const response = await apiClient.register({
        email,
        factory_name: factoryName,
        return_to: returnToParam,
        entry: entryParam || undefined,
      })
      setIsNewUser(true)
      setDevMagicLink(response.dev_magic_link || null)
      setStep("check-email")
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'status' in err && err.status === 409) {
        setError("Аккаунт уже есть — войдите.")
      } else if (err && typeof err === 'object' && 'detail' in err) {
        setError(String(err.detail))
      } else {
        setError("Не удалось зарегистрироваться. Попробуйте позже.")
      }
    } finally {
      setIsLoading(false)
    }
  }

  const resetFlow = () => {
    setStep("form")
    setError(null)
    setDevMagicLink(null)
  }

  // Animation variants for switching modes (fade + 8px, no horizontal slide)
  const modeVariants = {
    initial: { opacity: 0, y: 8 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: -8 },
  }

  // Animation variants for changing steps (check-email step)
  const stepVariants = {
    initial: { opacity: 0, scale: 0.98 },
    animate: { opacity: 1, scale: 1 },
    exit: { opacity: 0, scale: 0.98 },
  }

  return (
    <div className="flex items-center justify-center min-h-[100dvh] bg-[#f3f6f8] px-4 py-8">
      <Card className="w-full max-w-[420px] overflow-hidden bg-white border border-[#d7dde2] shadow-sm rounded-xl">
        <AnimatePresence mode="wait">
          {step === "form" ? (
            <motion.div
              key="form-step"
              variants={stepVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              transition={{ duration: 0.2, ease: "easeOut" }}
            >
              {/* Mode switch - always visible on the form step */}
              <div className="flex border-b border-[#d7dde2] bg-white">
                <button
                  type="button"
                  onClick={() => {
                    setActiveMode("login")
                    setError(null)
                  }}
                  className={`flex-1 py-3 text-center text-sm font-semibold border-b-2 transition-all duration-150 cursor-pointer ${
                    activeMode === "login"
                      ? "border-[#c7ff00] text-[#171a1d]"
                      : "border-transparent text-[#66707a] hover:text-[#171a1d]"
                  }`}
                >
                  Войти
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setActiveMode("register")
                    setError(null)
                  }}
                  className={`flex-1 py-3 text-center text-sm font-semibold border-b-2 transition-all duration-150 cursor-pointer ${
                    activeMode === "register"
                      ? "border-[#c7ff00] text-[#171a1d]"
                      : "border-transparent text-[#66707a] hover:text-[#171a1d]"
                  }`}
                >
                  Создать аккаунт
                </button>
              </div>

              <AnimatePresence mode="wait">
                {activeMode === "login" ? (
                  <motion.form
                    key="login-form"
                    onSubmit={handleLoginSubmit}
                    variants={modeVariants}
                    initial="initial"
                    animate="animate"
                    exit="exit"
                    transition={{ duration: 0.18, ease: "easeOut" }}
                    className="p-6 space-y-4"
                  >
                    <div className="space-y-1.5">
                      <Label htmlFor="email" className="text-xs font-semibold text-[#171a1d]">Email</Label>
                      <Input
                        id="email"
                        type="email"
                        placeholder="director@mebel-pro.ru"
                        required
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        autoComplete="email"
                        className="h-10 border-[#d7dde2] focus-visible:ring-[#c7ff00] text-[#171a1d] placeholder:text-[#66707a]/50 text-sm"
                      />
                    </div>

                    {error && (
                      <p className="text-xs text-red-500 font-medium">{error}</p>
                    )}

                    <Button 
                      type="submit" 
                      className="w-full h-10 bg-[#c7ff00] hover:bg-[#aee600] text-[#171a1d] font-semibold active:scale-[0.98] transition-all duration-150 rounded-lg cursor-pointer"
                      disabled={isLoading}
                    >
                      {isLoading ? "Отправка..." : "Получить ссылку"}
                    </Button>
                  </motion.form>
                ) : (
                  <motion.form
                    key="register-form"
                    onSubmit={handleRegisterSubmit}
                    variants={modeVariants}
                    initial="initial"
                    animate="animate"
                    exit="exit"
                    transition={{ duration: 0.18, ease: "easeOut" }}
                    className="p-6 space-y-4"
                  >
                    <div className="space-y-1.5">
                      <Label htmlFor="reg-email" className="text-xs font-semibold text-[#171a1d]">Email</Label>
                      <Input
                        id="reg-email"
                        type="email"
                        placeholder="director@mebel-pro.ru"
                        required
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        autoComplete="email"
                        className="h-10 border-[#d7dde2] focus-visible:ring-[#c7ff00] text-[#171a1d] placeholder:text-[#66707a]/50 text-sm"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <Label htmlFor="factory-name" className="text-xs font-semibold text-[#171a1d]">Название фабрики</Label>
                      <div className="relative">
                        <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#66707a]/70" />
                        <Input
                          id="factory-name"
                          type="text"
                          placeholder="ООО Мебель-Про"
                          required
                          value={factoryName}
                          onChange={(e) => setFactoryName(e.target.value)}
                          className="h-10 pl-10 border-[#d7dde2] focus-visible:ring-[#c7ff00] text-[#171a1d] placeholder:text-[#66707a]/50 text-sm"
                        />
                      </div>
                    </div>

                    {error && (
                      <p className="text-xs text-red-500 font-medium">{error}</p>
                    )}

                    <Button 
                      type="submit" 
                      className="w-full h-10 bg-[#c7ff00] hover:bg-[#aee600] text-[#171a1d] font-semibold active:scale-[0.98] transition-all duration-150 rounded-lg cursor-pointer"
                      disabled={isLoading}
                    >
                      {isLoading ? "Регистрация..." : "Зарегистрироваться"}
                    </Button>
                    
                    <p className="text-[10px] text-center text-[#66707a] leading-relaxed">
                      Нажимая кнопку, вы соглашаетесь с правилами сервиса
                    </p>
                  </motion.form>
                )}
              </AnimatePresence>
            </motion.div>
          ) : (
            <motion.div
              key="check-email-step"
              variants={stepVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              transition={{ duration: 0.2, ease: "easeOut" }}
              className="p-6 text-center space-y-4 bg-white"
            >
              <div className="flex justify-center">
                <div className="w-12 h-12 rounded-full bg-[#c7ff00]/10 flex items-center justify-center">
                  <Mail className="w-6 h-6 text-[#171a1d]" />
                </div>
              </div>
              
              <div className="space-y-1">
                <CardTitle className="text-lg font-bold text-[#171a1d]">Проверьте почту</CardTitle>
                <CardDescription className="text-xs text-[#66707a] px-2 leading-relaxed">
                  {isNewUser
                    ? `Ссылка для завершения регистрации отправлена на ${email}`
                    : `Если аккаунт с таким адресом есть, ссылка придёт на почту ${email}`
                  }
                </CardDescription>
              </div>

              {devMagicLink && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-left">
                  <p className="text-[10px] font-bold text-amber-800 mb-1">
                    🔧 DEV MODE — Magic Link:
                  </p>
                  <a
                    href={devMagicLink}
                    className="text-xs text-blue-600 hover:underline break-all"
                  >
                    {devMagicLink}
                  </a>
                </div>
              )}

              <div className="bg-[#f3f6f8] rounded-xl p-3 text-xs text-[#66707a] text-left space-y-2">
                <p className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                  Ссылка действительно в течение 15 минут.
                </p>
                <p className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                  Проверьте папку «Спам», если письма долго нет.
                </p>
              </div>

              <Button
                variant="outline"
                className="w-full h-10 border-[#d7dde2] hover:bg-[#f3f6f8] text-[#171a1d] font-semibold active:scale-[0.98] transition-all duration-150 rounded-lg cursor-pointer text-xs"
                onClick={resetFlow}
              >
                <ArrowLeft className="w-4 h-4 mr-1.5" />
                Изменить email
              </Button>
            </motion.div>
          )}
        </AnimatePresence>
      </Card>
    </div>
  )
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-[100dvh] bg-[#f3f6f8]">
        <div className="text-sm text-[#66707a]">Загрузка...</div>
      </div>
    }>
      <LoginFormInner />
    </Suspense>
  )
}
