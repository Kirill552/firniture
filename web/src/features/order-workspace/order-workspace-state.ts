export const ORDER_WORKSPACE_STAGE_KEYS = [
  'input',
  'parameters',
  'clarification',
  'specification',
  'validation',
  'export',
] as const

export type OrderWorkspaceStageKey = typeof ORDER_WORKSPACE_STAGE_KEYS[number]

export type OrderWorkspaceStageStatus = 'complete' | 'current' | 'available' | 'blocked'

export type OrderWorkspaceStage = {
  key: OrderWorkspaceStageKey
  status: OrderWorkspaceStageStatus
}

export type OrderWorkspaceUser = {
  isGuest: boolean
  canExport: boolean
}

export type OrderWorkspaceOrder = {
  revision: number
  approvedRevision: number | null
  machine: boolean
}

export type OrderWorkspaceStateInput = {
  user: OrderWorkspaceUser
  order: OrderWorkspaceOrder
  completedStages: readonly OrderWorkspaceStageKey[]
  currentStage?: OrderWorkspaceStageKey
}

function isExportAllowed(input: OrderWorkspaceStateInput): boolean {
  if (input.user.isGuest) return false
  if (!input.user.canExport) return false
  if (input.order.approvedRevision === null) return false
  if (input.order.approvedRevision < input.order.revision) return false
  return true
}

function isStageReachable(
  stage: OrderWorkspaceStageKey,
  index: number,
  completed: Set<OrderWorkspaceStageKey>,
  exportAllowed: boolean,
): boolean {
  if (stage === 'export' && !exportAllowed) return false
  if (index === 0) return true
  const previous = ORDER_WORKSPACE_STAGE_KEYS[index - 1]
  return completed.has(previous)
}

export function projectOrderWorkspaceStages(
  input: OrderWorkspaceStateInput,
): OrderWorkspaceStage[] {
  const completed = new Set(input.completedStages)
  const exportAllowed = isExportAllowed(input)

  const stages: OrderWorkspaceStage[] = ORDER_WORKSPACE_STAGE_KEYS.map((stage, index) => {
    if (completed.has(stage)) {
      return { key: stage, status: 'complete' }
    }

    const reachable = isStageReachable(stage, index, completed, exportAllowed)
    if (!reachable) {
      return { key: stage, status: 'blocked' }
    }

    return { key: stage, status: 'available' }
  })

  const explicitCurrentIndex = stages.findIndex(
    (stage) => stage.status === 'available' && stage.key === input.currentStage,
  )
  const targetIndex =
    explicitCurrentIndex !== -1 ? explicitCurrentIndex : stages.findIndex((stage) => stage.status === 'available')

  if (targetIndex !== -1) {
    stages[targetIndex].status = 'current'
  }

  return stages
}
