import { motion } from 'framer-motion'
import { LucideIcon, Database, Search } from 'lucide-react'
import { Button } from './button'
import { cn } from '@/lib/utils'

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description: string
  action?: {
    label: string
    onClick: () => void
    variant?: 'default' | 'outline' | 'secondary'
  }
  className?: string
}

export function EmptyState({ 
  icon: Icon, 
  title, 
  description, 
  action, 
  className 
}: EmptyStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      className={cn(
        'flex flex-col items-center justify-center text-center py-12 px-6',
        className
      )}
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
        className="mb-6"
      >
        <div className="w-16 h-16 bg-muted/20 rounded-full flex items-center justify-center">
          <Icon className="w-8 h-8 text-muted-foreground" />
        </div>
      </motion.div>
      
      <motion.h3
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4, delay: 0.2 }}
        className="text-lg font-semibold text-foreground mb-2"
      >
        {title}
      </motion.h3>
      
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4, delay: 0.3 }}
        className="text-muted-foreground max-w-md mb-6 leading-relaxed"
      >
        {description}
      </motion.p>
      
      {action && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.4 }}
        >
          <Button 
            onClick={action.onClick}
            variant={action.variant || 'default'}
            className="shadow-sm"
          >
            {action.label}
          </Button>
        </motion.div>
      )}
    </motion.div>
  )
}

// Специализированные компоненты для разных случаев

export function EmptyDataState({ 
  title = "Данные отсутствуют", 
  description = "Здесь пока нет данных для отображения.",
  ...props 
}: Partial<EmptyStateProps>) {
  return (
    <EmptyState
      icon={props.icon || Database}
      title={title}
      description={description}
      {...props}
    />
  )
}

export function EmptySearchState({ 
  searchTerm,
  onClearSearch,
  ...props 
}: Partial<EmptyStateProps> & { 
  searchTerm?: string
  onClearSearch?: () => void 
}) {  
  return (
    <EmptyState
      icon={Search}
      title="Ничего не найдено"
      description={
        searchTerm 
          ? `По запросу "${searchTerm}" ничего не найдено. Попробуйте изменить поисковый запрос.`
          : "Попробуйте изменить параметры поиска или фильтры."
      }
      action={onClearSearch ? {
        label: "Очистить поиск",
        onClick: onClearSearch,
        variant: "outline"
      } : undefined}
      {...props}
    />
  )
}