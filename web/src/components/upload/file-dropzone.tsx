"use client"
import React, { useCallback, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/lib/utils'
import { Upload, CheckCircle2, AlertTriangle, FileIcon } from 'lucide-react'

export type RejectCode = 'file-too-large' | 'too-many-files' | 'invalid-type'
export interface RejectReason {
  file: File
  code: RejectCode
  message: string
}

export interface FileDropzoneProps {
  onFiles: (files: File[]) => void
  onReject?: (reasons: RejectReason[]) => void
  accept?: Record<string, string[]> | string[]
  maxSize?: number // bytes
  maxFiles?: number
  multiple?: boolean
  disabled?: boolean
  className?: string
  description?: string
  idleIcon?: React.ReactNode
  dragIcon?: React.ReactNode
  acceptIcon?: React.ReactNode
  rejectIcon?: React.ReactNode
  ariaLabel?: string
  autoFocus?: boolean
  highlightOnFocus?: boolean
  capture?: boolean | 'environment' | 'user'
}

const DEFAULT_MAX_SIZE = 10 * 1024 * 1024

function normalizeAccept(accept?: FileDropzoneProps['accept']) {
  if (!accept) return null
  if (Array.isArray(accept)) return accept.map(a => a.toLowerCase())
  // object form: { 'image/*': ['.png','.jpg'] }
  const exts: string[] = []
  Object.entries(accept).forEach(([mime, arr]) => {
    exts.push(mime.toLowerCase())
    arr.forEach(x => exts.push(x.toLowerCase()))
  })
  return exts
}

export const FileDropzone: React.FC<FileDropzoneProps> = ({
  onFiles,
  onReject,
  accept,
  maxSize = DEFAULT_MAX_SIZE,
  maxFiles = 5,
  multiple,
  disabled,
  className,
  description = 'Перетащите файлы сюда или нажмите для выбора',
  idleIcon,
  dragIcon,
  acceptIcon,
  rejectIcon,
  ariaLabel,
  autoFocus,
  highlightOnFocus = true,
  capture,
}) => {
  const inputRef = useRef<HTMLInputElement | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const [dragAccept, setDragAccept] = useState<boolean | null>(null)
  const [shake, setShake] = useState(false)

  const normalizedAccept = normalizeAccept(accept)
  const allowMultiple = multiple ?? maxFiles > 1

  const evaluateFiles = useCallback((fileList: FileList | null) => {
    if (!fileList) return { valid: [], rejected: [] as RejectReason[] }
    const files = Array.from(fileList)
    const valid: File[] = []
    const rejected: RejectReason[] = []

    if (files.length > maxFiles) {
      files.slice(maxFiles).forEach(f => rejected.push({ file: f, code: 'too-many-files', message: `Превышен лимит файлов (${maxFiles})` }))
    }

    files.slice(0, maxFiles).forEach(file => {
      // type check
      if (normalizedAccept) {
        const lowerName = file.name.toLowerCase()
        const lowerType = file.type.toLowerCase()
        const ok = normalizedAccept.some(rule => {
          if (rule.endsWith('/*')) {
            return lowerType.startsWith(rule.replace('/*','/'))
          }
          if (rule.startsWith('.')) return lowerName.endsWith(rule)
          return lowerType === rule
        })
        if (!ok) {
          rejected.push({ file, code: 'invalid-type', message: 'Недопустимый тип файла' })
          return
        }
      }
      if (file.size > maxSize) {
        rejected.push({ file, code: 'file-too-large', message: `Размер > ${(maxSize/1024/1024).toFixed(1)}MB` })
        return
      }
      valid.push(file)
    })

    return { valid, rejected }
  }, [maxFiles, maxSize, normalizedAccept])

  const openDialog = () => {
    if (disabled) return
    inputRef.current?.click()
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { valid, rejected } = evaluateFiles(e.target.files)
    if (rejected.length) {
      onReject?.(rejected)
      triggerShake()
    }
    if (valid.length) onFiles(valid)
    e.target.value = '' // reset so same files can be selected again
  }

  const triggerShake = () => {
    setShake(true)
    setTimeout(() => setShake(false), 360)
  }

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (disabled) return
    if (!dragActive) setDragActive(true)
    if (e.dataTransfer.items) {
      const fileList: FileList = {
        length: e.dataTransfer.items.length,
        item: (index: number) => e.dataTransfer.items[index]?.getAsFile() || null,
        [Symbol.iterator]: function* () { for (let i=0;i<this.length;i++) { const f = this.item(i); if (f) yield f } }
      } as any
      const { rejected } = evaluateFiles(fileList)
      setDragAccept(rejected.length ? false : true)
    }
  }

  const onDragLeave = (e: React.DragEvent) => {
    if (e.currentTarget.contains(e.relatedTarget as Node)) return
    setDragActive(false)
    setDragAccept(null)
  }

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (disabled) return
    setDragActive(false)
    const { valid, rejected } = evaluateFiles(e.dataTransfer.files)
    setDragAccept(rejected.length ? false : true)
    if (rejected.length) {
      onReject?.(rejected)
      triggerShake()
    }
    if (valid.length) onFiles(valid)
  }

  const state: 'idle' | 'drag' | 'accept' | 'reject' | 'disabled' = disabled
    ? 'disabled'
    : dragAccept === true
      ? 'accept'
      : dragAccept === false
        ? 'reject'
        : dragActive
          ? 'drag'
          : 'idle'

  const icons: Record<string, React.ReactNode> = {
    idle: idleIcon ?? <Upload className="h-5 w-5" />,
    drag: dragIcon ?? <Upload className="h-5 w-5" />,
    accept: acceptIcon ?? <CheckCircle2 className="h-5 w-5 text-green-500" />,
    reject: rejectIcon ?? <AlertTriangle className="h-5 w-5 text-red-500" />,
    disabled: <FileIcon className="h-5 w-5" />
  }

  return (
    <div className="w-full">
      <input
        ref={inputRef}
        type="file"
        multiple={allowMultiple}
        className="hidden"
        aria-hidden
        onChange={handleInputChange}
        accept={Array.isArray(accept) ? accept.join(',') : undefined}
        {...(capture ? { capture: capture as any } : {})}
      />
      <motion.button
        type="button"
        role="button"
        tabIndex={0}
        aria-label={ariaLabel || 'Зона загрузки файлов'}
        aria-disabled={disabled}
        onClick={openDialog}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openDialog() } }}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        autoFocus={autoFocus}
        className={cn(
          'relative flex w-full flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-6 text-center outline-none transition-colors',
          'bg-muted/30 hover:bg-muted/50 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
          state === 'drag' && 'border-primary',
          state === 'accept' && 'border-green-500 bg-green-500/5',
          state === 'reject' && 'border-red-500 bg-red-500/5',
          disabled && 'opacity-50 cursor-not-allowed',
          highlightOnFocus && 'focus-visible:ring-offset-background',
          className
        )}
        initial={false}
        animate={{
          scale: state === 'drag' ? 1.02 : 1,
          boxShadow: state === 'accept'
            ? '0 0 0 2px rgba(34,197,94,0.3), 0 4px 12px -2px rgba(34,197,94,0.25)'
            : state === 'reject'
              ? '0 0 0 2px rgba(239,68,68,0.3), 0 4px 12px -2px rgba(239,68,68,0.25)'
              : '0 0 0 0 rgba(0,0,0,0)'
        }}
        whileTap={{ scale: 0.97 }}
        data-state={state}
      >
        <motion.div
          key={state}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: 0.18 }}
          className={cn('flex flex-col items-center gap-2 text-sm text-muted-foreground')}
        >
          {icons[state]}
          <span className="font-medium text-foreground">
            {state === 'idle' && 'Перетащите сюда файлы'}
            {state === 'drag' && 'Отпустите для добавления'}
            {state === 'accept' && 'Отпустите — всё ок'}
            {state === 'reject' && 'Некоторые файлы не подходят'}
            {state === 'disabled' && 'Загрузка недоступна'}
          </span>
          {description && <span className="text-xs opacity-70 max-w-[320px] leading-relaxed">{description}</span>}
        </motion.div>
        <AnimatePresence>
          {shake && (
            <motion.div
              className="pointer-events-none absolute inset-0 rounded-lg"
              initial={{ x: 0 }}
              animate={{ x: [0, -6, 6, -4, 4, -2, 2, 0] }}
              transition={{ duration: 0.36, ease: 'easeInOut' }}
            />
          )}
        </AnimatePresence>
      </motion.button>
    </div>
  )
}
