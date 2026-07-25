'use client'

import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useRouter } from 'next/navigation'

interface GuestAuthGateProps {
  isOpen: boolean
  onClose: () => void
  orderId: string | null
}

export function GuestAuthGate({ isOpen, onClose, orderId }: GuestAuthGateProps) {
  const router = useRouter()

  if (!isOpen || !orderId) return null

  const handleAction = (mode: 'login' | 'register') => {
    // URL-encoded return target which resolveAuthReturnTarget will evaluate
    const returnTo = `/bom?orderId=${orderId}`
    router.push(`/login?mode=${mode}&entry=save-draft&returnTo=${encodeURIComponent(returnTo)}`)
  }

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center">
        {/* Backdrop overlay */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="absolute inset-0 bg-[#171a1d]/40 backdrop-blur-[2px]"
        />

        {/* Modal content */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 10 }}
          transition={{ duration: 0.2, ease: 'easeOut' }}
          className="relative w-full max-w-[420px] bg-white border border-[#d7dde2] shadow-xl rounded-xl p-6 z-10 mx-4"
        >
          {/* Close button */}
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-[#66707a] hover:text-[#171a1d] transition-colors p-1 rounded-lg hover:bg-[#f3f6f8] cursor-pointer"
            aria-label="Закрыть"
          >
            <X className="w-4 h-4" />
          </button>

          <div className="space-y-4">
            <div className="flex justify-center">
              <div className="w-10 h-10 rounded-full bg-[#c7ff00]/10 flex items-center justify-center text-[#171a1d]">
                <Sparkles className="w-5 h-5" />
              </div>
            </div>

            <div className="text-center space-y-1.5">
              <h3 className="text-base font-bold text-[#171a1d]">Черновик готов</h3>
              <p className="text-xs text-[#66707a] leading-relaxed px-1">
                Войдите или создайте аккаунт, чтобы закрепить заказ за вашей фабрикой и получить PDF/DXF файлы.
              </p>
            </div>

            <div className="flex flex-col gap-2 pt-2">
              <Button
                onClick={() => handleAction('register')}
                className="w-full h-10 bg-[#c7ff00] hover:bg-[#aee600] text-[#171a1d] font-semibold transition-all duration-150 rounded-lg cursor-pointer text-xs"
              >
                Создать аккаунт
              </Button>
              <Button
                onClick={() => handleAction('login')}
                variant="outline"
                className="w-full h-10 border-[#d7dde2] hover:bg-[#f3f6f8] text-[#171a1d] font-semibold transition-all duration-150 rounded-lg cursor-pointer text-xs"
              >
                Войти в аккаунт
              </Button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}
