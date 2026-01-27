'use client'

import { useRouter } from "next/navigation"
import { useEffect } from "react"

/**
 * Редирект на новый Vision-first флоу.
 * Старый флоу удалён — теперь всё через /new.
 */
export default function NewOrderRedirect() {
  const router = useRouter()

  useEffect(() => {
    router.replace('/new')
  }, [router])

  return null
}
