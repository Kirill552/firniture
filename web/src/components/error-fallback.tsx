"use client"

import { motion } from 'framer-motion'
import { AlertTriangle, RefreshCw, Home, Bug } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useToast } from '@/hooks/use-toast'

interface ErrorFallbackProps {
  error: Error & { digest?: string }
  reset: () => void
}

export function ErrorFallback({ error, reset }: ErrorFallbackProps) {
  const { error: showErrorToast } = useToast()

  const handleReportError = () => {
    showErrorToast(
      "Ошибка отправлена", 
      "Спасибо за отчет! Мы работаем над исправлением."
    )
  }

  return (
    <div className="min-h-[400px] flex items-center justify-center p-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="text-center space-y-6 max-w-md"
      >
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ 
            duration: 0.5, 
            delay: 0.1, 
            type: 'spring', 
            stiffness: 200 
          }}
          className="w-16 h-16 bg-destructive/10 rounded-full flex items-center justify-center mx-auto"
        >
          <AlertTriangle className="w-8 h-8 text-destructive" />
        </motion.div>
        
        <div className="space-y-2">
          <h2 className="text-xl font-semibold text-foreground">
            Что-то пошло не так
          </h2>
          <p className="text-muted-foreground text-sm leading-relaxed">
            Произошла неожиданная ошибка. Попробуйте обновить страницу или вернитесь позже.
          </p>
        </div>

        {process.env.NODE_ENV === 'development' && (
          <motion.details
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="text-left bg-muted/20 rounded-md p-4"
          >
            <summary className="cursor-pointer text-sm font-medium mb-2">
              Подробности ошибки (для разработчика)
            </summary>
            <pre className="text-xs text-muted-foreground overflow-auto">
              {error.message}
              {error.digest && `\nDigest: ${error.digest}`}
            </pre>
          </motion.details>
        )}

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Button 
            onClick={reset} 
            className="inline-flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Попробовать снова
          </Button>
          
          <Button 
            variant="outline" 
            onClick={() => window.location.href = '/dashboard'}
            className="inline-flex items-center gap-2"
          >
            <Home className="w-4 h-4" />
            На главную
          </Button>
        </div>

        <Button 
          variant="ghost" 
          size="sm"
          onClick={handleReportError}
          className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground"
        >
          <Bug className="w-4 h-4" />
          Сообщить об ошибке
        </Button>
      </motion.div>
    </div>
  )
}

// Компонент для ошибок загрузки данных
export function DataErrorFallback({ 
  error, 
  retry, 
  className 
}: { 
  error: Error
  retry?: () => void
  className?: string 
}) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className={`text-center py-8 px-4 ${className}`}
    >
      <div className="w-12 h-12 bg-destructive/10 rounded-full flex items-center justify-center mx-auto mb-4">
        <AlertTriangle className="w-6 h-6 text-destructive" />
      </div>
      
      <h3 className="text-lg font-medium text-foreground mb-2">
        Ошибка загрузки данных
      </h3>
      
      <p className="text-muted-foreground text-sm mb-4">
        {error.message || "Не удалось загрузить данные. Проверьте подключение к интернету."}
      </p>
      
      {retry && (
        <Button 
          onClick={retry} 
          size="sm"
          className="inline-flex items-center gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          Повторить
        </Button>
      )}
    </motion.div>
  )
}