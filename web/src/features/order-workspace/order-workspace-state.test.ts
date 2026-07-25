import { describe, expect, it } from 'vitest'

import { projectOrderWorkspaceStages } from './order-workspace-state'

const baseUser = {
  isGuest: false,
  canExport: true,
}

describe('projectOrderWorkspaceStages', () => {
  it('marks the first stage as current by default', () => {
    const stages = projectOrderWorkspaceStages({
      user: baseUser,
      order: { revision: 1, approvedRevision: null, machine: false },
      completedStages: [],
    })

    expect(stages).toEqual([
      { key: 'input', status: 'current' },
      { key: 'parameters', status: 'blocked' },
      { key: 'clarification', status: 'blocked' },
      { key: 'specification', status: 'blocked' },
      { key: 'validation', status: 'blocked' },
      { key: 'export', status: 'blocked' },
    ])
  })

  it('progresses linearly when stages are completed', () => {
    const stages = projectOrderWorkspaceStages({
      user: baseUser,
      order: { revision: 1, approvedRevision: null, machine: false },
      completedStages: ['input', 'parameters', 'clarification', 'specification'],
      currentStage: 'validation',
    })

    expect(stages).toEqual([
      { key: 'input', status: 'complete' },
      { key: 'parameters', status: 'complete' },
      { key: 'clarification', status: 'complete' },
      { key: 'specification', status: 'complete' },
      { key: 'validation', status: 'current' },
      { key: 'export', status: 'blocked' },
    ])
  })

  it('blocks export for guests', () => {
    const stages = projectOrderWorkspaceStages({
      user: { isGuest: true, canExport: false },
      order: { revision: 1, approvedRevision: 1, machine: false },
      completedStages: ['input', 'parameters', 'clarification', 'specification', 'validation'],
      currentStage: 'export',
    })

    expect(stages.find((stage) => stage.key === 'export')).toEqual({
      key: 'export',
      status: 'blocked',
    })
    expect(stages.filter((stage) => stage.status === 'current')).toHaveLength(0)
  })

  it('blocks export for authenticated users without export permission', () => {
    const stages = projectOrderWorkspaceStages({
      user: { isGuest: false, canExport: false },
      order: { revision: 1, approvedRevision: 1, machine: false },
      completedStages: ['input', 'parameters', 'clarification', 'specification', 'validation'],
      currentStage: 'export',
    })

    expect(stages.find((stage) => stage.key === 'export')).toEqual({
      key: 'export',
      status: 'blocked',
    })
  })

  it('blocks export until the order is approved', () => {
    const stages = projectOrderWorkspaceStages({
      user: baseUser,
      order: { revision: 1, approvedRevision: null, machine: false },
      completedStages: ['input', 'parameters', 'clarification', 'specification'],
      currentStage: 'validation',
    })

    expect(stages.find((stage) => stage.key === 'export')).toEqual({
      key: 'export',
      status: 'blocked',
    })
    expect(stages.find((stage) => stage.key === 'validation')).toEqual({
      key: 'validation',
      status: 'current',
    })
  })

  it('marks export as current after approval', () => {
    const stages = projectOrderWorkspaceStages({
      user: baseUser,
      order: { revision: 1, approvedRevision: 1, machine: false },
      completedStages: ['input', 'parameters', 'clarification', 'specification', 'validation'],
      currentStage: 'export',
    })

    expect(stages.find((stage) => stage.key === 'export')).toEqual({
      key: 'export',
      status: 'current',
    })
  })

  it('reblocks export on a newer revision after approval', () => {
    const stages = projectOrderWorkspaceStages({
      user: baseUser,
      order: { revision: 6, approvedRevision: 5, machine: false },
      completedStages: ['input', 'parameters', 'clarification', 'specification', 'validation'],
      currentStage: 'export',
    })

    expect(stages.find((stage) => stage.key === 'export')).toEqual({
      key: 'export',
      status: 'blocked',
    })
  })

  it('does not block PDF/DXF export when the machine flag is set', () => {
    const stages = projectOrderWorkspaceStages({
      user: baseUser,
      order: { revision: 1, approvedRevision: 1, machine: true },
      completedStages: ['input', 'parameters', 'clarification', 'specification', 'validation'],
      currentStage: 'export',
    })

    expect(stages.find((stage) => stage.key === 'export')).toEqual({
      key: 'export',
      status: 'current',
    })
  })
})
