'use client'

import { useState } from "react"
import { useRouter } from "next/navigation"
import { motion, AnimatePresence } from "framer-motion"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ArrowLeft } from "lucide-react"

type AuthStep = "enter-email" | "login" | "register"

// Mock API call
const checkUserExists = async (email: string): Promise<boolean> => {
  console.log(`Checking if ${email} exists...`)
  await new Promise(resolve => setTimeout(resolve, 500)) // Simulate network delay
  // In a real app, you'd make a request to your backend.
  // For this mock, let's say users with `registered` in their email exist.
  const exists = email.includes("registered")
  console.log(`User exists: ${exists}`)
  return exists
}

export default function SmartLoginPage() {
  const router = useRouter()
  const [step, setStep] = useState<AuthStep>("enter-email")
  const [email, setEmail] = useState("")
  const [isLoading, setIsLoading] = useState(false)

  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email) return
    setIsLoading(true)
    const userExists = await checkUserExists(email)
    setIsLoading(false)
    setStep(userExists ? "login" : "register")
  }

  const handleLogin = async () => {
    setIsLoading(true)
    await new Promise(resolve => setTimeout(resolve, 1000))
    router.push('/dashboard')
  }

  const handleRegister = async () => {
    setIsLoading(true)
    await new Promise(resolve => setTimeout(resolve, 1000))
    router.push('/dashboard')
  }

  const resetFlow = () => {
    setStep("enter-email")
    // setEmail("") // Optionally keep email for better UX
  }

  const formVariants = {
    initial: { opacity: 0, x: 300 },
    animate: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: -300 },
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-950">
      <Card className="w-[400px] h-[350px] overflow-hidden relative">
        <AnimatePresence initial={false} mode="wait">
          <motion.div
            key={step}
            variants={formVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={{ type: "tween", duration: 0.35, ease: "easeInOut" }}
            className="h-full w-full absolute"
          >
            {step === "enter-email" && (
              <form onSubmit={handleEmailSubmit} className="h-full">
                <CardHeader>
                  <CardTitle>Войдите или создайте аккаунт</CardTitle>
                  <CardDescription>Введите ваш email для продолжения.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <Input 
                      id="email" 
                      type="email" 
                      placeholder="email@example.com" 
                      required 
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                    />
                  </div>
                  <Button type="submit" className="w-full" disabled={isLoading}>
                    {isLoading ? "Проверка..." : "Продолжить"}
                  </Button>
                </CardContent>
              </form>
            )}

            {step === "login" && (
              <div className="h-full">
                <CardHeader>
                   <button onClick={resetFlow} className="flex items-center text-sm text-gray-500 hover:text-primary transition-colors"><ArrowLeft className="w-4 h-4 mr-1"/> {email}</button>
                  <CardTitle>С возвращением!</CardTitle>
                  <CardDescription>Введите пароль, чтобы войти.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <form onSubmit={(e) => { e.preventDefault(); handleLogin(); }}>
                    <div className="space-y-2">
                      <Label htmlFor="password">Пароль</Label>
                      <Input id="password" type="password" required />
                    </div>
                    <Button type="submit" className="w-full" disabled={isLoading}>
                      {isLoading ? "Вход..." : "Войти"}
                    </Button>
                  </form>
                  <Button onClick={handleLogin} variant="outline" className="w-full" disabled={isLoading}>
                    {isLoading ? "Вход..." : "Войти с помощью Passkey"}
                  </Button>
                </CardContent>
              </div>
            )}

            {step === "register" && (
              <div className="h-full">
                 <CardHeader>
                   <button onClick={resetFlow} className="flex items-center text-sm text-gray-500 hover:text-primary transition-colors"><ArrowLeft className="w-4 h-4 mr-1"/> {email}</button>
                  <CardTitle>Создать аккаунт</CardTitle>
                  <CardDescription>Мы не нашли аккаунт с этим email. Создайте новый, получив волшебную ссылку.</CardDescription>
                </CardHeader>
                <CardContent>
                  <Button onClick={handleRegister} className="w-full" disabled={isLoading}>
                    {isLoading ? "Отправка..." : "Отправить волшебную ссылку"}
                  </Button>
                </CardContent>
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      </Card>
    </div>
  )
}
