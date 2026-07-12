import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  type AnalyticsEvent,
  type ConsentStatus,
  type SensitiveProps,
  type TrackEnvelope,
  type OrderCreatedEvent,
  type BomApprovedEvent,
  type CamValidationCompletedEvent,
  type ArtifactDownloadedEvent,
  type OrderReviewedEvent,
  getConsent,
  setConsent,
  track,
  registerSink,
  unregisterSink,
  redactProperties,
} from './analytics'

// ─── localStorage mock ──────────────────────────────────────────────────────

const store = new Map<string, string>()

beforeEach(() => {
  store.clear()
  unregisterSink()

  vi.stubGlobal('window', { location: { href: '' } })
  vi.stubGlobal('localStorage', {
    getItem: (k: string) => store.get(k) ?? null,
    setItem: (k: string, v: string) => {
      store.set(k, v)
    },
    removeItem: (k: string) => {
      store.delete(k)
    },
  })
})

// ─── Consent ────────────────────────────────────────────────────────────────

describe('consent', () => {
  it('returns pending when no value stored', () => {
    expect(getConsent()).toBe('pending')
  })

  it('persists granted', () => {
    setConsent('granted')
    expect(getConsent()).toBe('granted')
  })

  it('persists denied', () => {
    setConsent('denied')
    expect(getConsent()).toBe('denied')
  })

  it('returns pending for unknown string', () => {
    store.set('analytics_consent', 'bogus')
    expect(getConsent()).toBe('pending')
  })
})

// ─── Consent – localStorage failures ────────────────────────────────────────

describe('consent – localStorage failures', () => {
  it('getConsent returns pending when getItem throws', () => {
    vi.stubGlobal('localStorage', {
      getItem: () => {
        throw new Error('SecurityError: storage disabled')
      },
      setItem: () => {},
    })
    expect(getConsent()).toBe('pending')
  })

  it('setConsent does not throw when setItem throws', () => {
    vi.stubGlobal('localStorage', {
      getItem: () => null,
      setItem: () => {
        throw new Error('QuotaExceededError')
      },
    })
    expect(() => setConsent('granted')).not.toThrow()
  })

  it('getConsent returns pending when localStorage is entirely undefined', () => {
    vi.stubGlobal('localStorage', undefined)
    expect(getConsent()).toBe('pending')
  })

  it('setConsent does not throw when localStorage is entirely undefined', () => {
    vi.stubGlobal('localStorage', undefined)
    expect(() => setConsent('granted')).not.toThrow()
  })
})

// ─── Redaction ──────────────────────────────────────────────────────────────

describe('redactProperties', () => {
  it('redacts known dimension keys', () => {
    const result = redactProperties({
      width_mm: 1200,
      height_mm: 800,
      depth_mm: 400,
    })
    expect(result).toEqual({
      width_mm: '[REDACTED]',
      height_mm: '[REDACTED]',
      depth_mm: '[REDACTED]',
    })
  })

  it('redacts sketch/image keys', () => {
    const result = redactProperties({
      sketch_url: 'https://example.com/img.png',
      image_data: 'base64blob',
    })
    expect(result).toEqual({
      sketch_url: '[REDACTED]',
      image_data: '[REDACTED]',
    })
  })

  it('preserves non-sensitive keys', () => {
    const result = redactProperties({
      order_id: 'abc-123',
      item_count: 5,
    })
    expect(result).toEqual({ order_id: 'abc-123', item_count: 5 })
  })

  it('recurses into nested objects', () => {
    const result = redactProperties({
      nested: { width_mm: 999, safe: 'ok' },
    })
    expect(result).toEqual({
      nested: { width_mm: '[REDACTED]', safe: 'ok' },
    })
  })

  it('passes arrays through unchanged', () => {
    const result = redactProperties({ tags: ['a', 'b'] })
    expect(result).toEqual({ tags: ['a', 'b'] })
  })
})

// ─── track() consent gate ───────────────────────────────────────────────────

describe('track – consent gate', () => {
  it('no-ops when consent is pending', () => {
    const sink = vi.fn()
    registerSink(sink)

    track({ name: 'order_created', properties: { order_id: '1', input_type: 'text', has_sketch: false } })
    expect(sink).not.toHaveBeenCalled()
  })

  it('no-ops when consent is denied', () => {
    setConsent('denied')
    const sink = vi.fn()
    registerSink(sink)

    track({ name: 'order_created', properties: { order_id: '1', input_type: 'text', has_sketch: false } })
    expect(sink).not.toHaveBeenCalled()
  })

  it('dispatches when consent is granted', () => {
    setConsent('granted')
    const sink = vi.fn()
    registerSink(sink)

    const event: TrackEnvelope = {
      name: 'order_created',
      properties: { order_id: 'o-1', input_type: 'sketch', has_sketch: true },
    }
    track(event)
    expect(sink).toHaveBeenCalledOnce()
    expect(sink).toHaveBeenCalledWith(event)
  })
})

// ─── track() end-to-end redaction ───────────────────────────────────────────

describe('track – end-to-end redaction', () => {
  it('strips dimension keys from sink payload', () => {
    setConsent('granted')
    const captured: AnalyticsEvent[] = []
    registerSink((e) => captured.push(e))

    const event: TrackEnvelope = {
      name: 'order_created',
      properties: {
        order_id: 'o-1',
        input_type: 'sketch',
        has_sketch: true,
        width_mm: 1200,
        height_mm: 800,
        depth_mm: 400,
      },
    }
    track(event)

    expect(captured).toHaveLength(1)
    const props = captured[0].properties as Record<string, unknown>
    expect(props.width_mm).toBe('[REDACTED]')
    expect(props.height_mm).toBe('[REDACTED]')
    expect(props.depth_mm).toBe('[REDACTED]')
    expect(props.order_id).toBe('o-1')
  })

  it('strips sketch/image keys from sink payload', () => {
    setConsent('granted')
    const captured: AnalyticsEvent[] = []
    registerSink((e) => captured.push(e))

    const event: TrackEnvelope = {
      name: 'cam_validation_completed',
      properties: {
        order_id: 'o-2',
        job_kind: 'DXF',
        status: 'Completed',
        sketch_data: 'data:image/png;base64,iVBOR...',
        image_url: 'https://example.com/sketch.png',
        sketch_content: '<svg>...</svg>',
        image_data: 'blob:raw',
      },
    }
    track(event)

    expect(captured).toHaveLength(1)
    const props = captured[0].properties as Record<string, unknown>
    expect(props.sketch_data).toBe('[REDACTED]')
    expect(props.image_url).toBe('[REDACTED]')
    expect(props.sketch_content).toBe('[REDACTED]')
    expect(props.image_data).toBe('[REDACTED]')
    expect(props.order_id).toBe('o-2')
    expect(props.job_kind).toBe('DXF')
  })

  it('redacts sensitive keys across all five event types', () => {
    setConsent('granted')
    const captured: AnalyticsEvent[] = []
    registerSink((e) => captured.push(e))

    const events: TrackEnvelope[] = [
      {
        name: 'order_created',
        properties: { order_id: '1', input_type: 'text', has_sketch: false, width_mm: 100 },
      },
      {
        name: 'order_reviewed',
        properties: { order_id: '2', input_type: 'image', sketch_url: 'https://x.com/a.png' },
      },
      {
        name: 'bom_approved',
        properties: { order_id: '3', item_count: 1, image_data: 'blob' },
      },
      {
        name: 'cam_validation_completed',
        properties: { order_id: '4', job_kind: 'DXF', status: 'ok', height_mm: 500 },
      },
      {
        name: 'artifact_downloaded',
        properties: { order_id: '5', artifact_type: 'DXF', job_kind: 'DXF', depth_mm: 200 },
      },
    ]

    for (const e of events) track(e)

    expect(captured).toHaveLength(5)
    for (const c of captured) {
      const p = c.properties as Record<string, unknown>
      if ('width_mm' in p) expect(p.width_mm).toBe('[REDACTED]')
      if ('height_mm' in p) expect(p.height_mm).toBe('[REDACTED]')
      if ('depth_mm' in p) expect(p.depth_mm).toBe('[REDACTED]')
      if ('sketch_url' in p) expect(p.sketch_url).toBe('[REDACTED]')
      if ('image_data' in p) expect(p.image_data).toBe('[REDACTED]')
    }
  })
})

// ─── track() without sink ───────────────────────────────────────────────────

describe('track – no sink', () => {
  it('does not throw when no sink registered', () => {
    setConsent('granted')
    expect(() =>
      track({ name: 'order_created', properties: { order_id: 'x', input_type: 'text', has_sketch: false } })
    ).not.toThrow()
  })
})

// ─── Event type compile-time check ──────────────────────────────────────────

describe('event type allowlist', () => {
  it('all five event names are assignable to AnalyticsEvent', () => {
    const events: AnalyticsEvent[] = [
      { name: 'order_created', properties: { order_id: '1', input_type: 'text', has_sketch: false } },
      { name: 'order_reviewed', properties: { order_id: '1', input_type: 'image' } },
      { name: 'bom_approved', properties: { order_id: '1', item_count: 3 } },
      { name: 'cam_validation_completed', properties: { order_id: '1', job_kind: 'DXF', status: 'Completed' } },
      { name: 'artifact_downloaded', properties: { order_id: '1', artifact_type: 'DXF', job_kind: 'DXF' } },
    ]
    expect(events).toHaveLength(5)
    expect(events.map((e) => e.name)).toEqual([
      'order_created',
      'order_reviewed',
      'bom_approved',
      'cam_validation_completed',
      'artifact_downloaded',
    ])
  })

  it('AnalyticsEvent is assignable to TrackEnvelope', () => {
    const event: AnalyticsEvent = {
      name: 'order_created',
      properties: { order_id: '1', input_type: 'text', has_sketch: false },
    }
    const envelope: TrackEnvelope = event
    expect(envelope.name).toBe('order_created')
  })
})

// ─── Sink lifecycle ─────────────────────────────────────────────────────────

describe('sink lifecycle', () => {
  it('unregisterSink stops dispatch', () => {
    setConsent('granted')
    const sink = vi.fn()
    registerSink(sink)

    track({ name: 'bom_approved', properties: { order_id: '1', item_count: 1 } })
    expect(sink).toHaveBeenCalledOnce()

    unregisterSink()
    track({ name: 'bom_approved', properties: { order_id: '2', item_count: 2 } })
    expect(sink).toHaveBeenCalledOnce() // no new call
  })
})
