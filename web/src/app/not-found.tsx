import Link from 'next/link'
import { FileQuestion, Home } from 'lucide-react'

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background to-muted/20">
      <div className="text-center space-y-8 px-4 max-w-md mx-auto">
        <div className="w-16 h-16 bg-muted/20 rounded-full flex items-center justify-center mx-auto">
          <FileQuestion className="w-8 h-8 text-muted-foreground" />
        </div>
        
        <div className="space-y-2">
          <h1 className="text-2xl font-bold text-foreground">Страница не найдена</h1>
          <p className="text-muted-foreground leading-relaxed">
            К сожалению, запрашиваемая страница не существует или была перемещена. 
            Проверьте правильность адреса или вернитесь на главную страницу.
          </p>
        </div>
        
        <div className="space-x-4">
          <Link
            href="/orders"
            className="inline-flex items-center px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
          >
            <Home className="w-4 h-4 mr-2" />
            На главную
          </Link>
          <Link 
            href="/" 
            className="inline-flex items-center px-4 py-2 border border-border rounded-md hover:bg-accent transition-colors"
          >
            На лендинг
          </Link>
        </div>
        
        <p className="text-sm text-muted-foreground">
          Код ошибки: <span className="font-mono font-medium">404</span>
        </p>
      </div>
    </div>
  )
}