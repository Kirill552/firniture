/**
 * Consent-safe analytics core.
 *
 * • Typed event allowlist — only the five whitelisted event names compile.
 * • Consent gate — every track() call no-ops when consent ≠ 'granted'.
 * • Automatic redaction — dimensions and sketch/image content are stripped.
 * • SSR-safe — all calls are silent on the server.
 */

// ─── Consent ────────────────────────────────────────────────────────────────

const CONSENT_KEY = 'analytics_consent'

export type ConsentStatus = 'granted' | 'denied' | 'pending'

export function getConsent(): ConsentStatus {
  if (typeof window === 'undefined') return 'pending'
  try {
    const raw = localStorage.getItem(CONSENT_KEY)
    if (raw === 'granted') return 'granted'
    if (raw === 'denied') return 'denied'
    return 'pending'
  } catch {
    return 'pending'
  }
}

export function setConsent(status: ConsentStatus): void {
  if (typeof window === 'undefined') return
  try {
    localStorage.setItem(CONSENT_KEY, status)
  } catch {
    // Storage unavailable or full — consent not persisted
  }
}

// ─── Event allowlist (discriminated union) ───────────────────────────────────

export interface OrderCreatedEvent {
  name: 'order_created'
  properties: {
    order_id: string
    input_type: string
    has_sketch: boolean
  }
}

export interface OrderReviewedEvent {
  name: 'order_reviewed'
  properties: {
    order_id: string
    input_type: string
  }
}

export interface BomApprovedEvent {
  name: 'bom_approved'
  properties: {
    order_id: string
    item_count: number
  }
}

export interface CamValidationCompletedEvent {
  name: 'cam_validation_completed'
  properties: {
    order_id: string
    job_kind: string
    status: string
  }
}

export interface ArtifactDownloadedEvent {
  name: 'artifact_downloaded'
  properties: {
    order_id: string
    artifact_type: string
    job_kind: string
  }
}

/** Closed union — only these five event names are trackable. */
export type AnalyticsEvent =
  | OrderCreatedEvent
  | OrderReviewedEvent
  | BomApprovedEvent
  | CamValidationCompletedEvent
  | ArtifactDownloadedEvent

// ─── Event property envelope ────────────────────────────────────────────────

/**
 * Sensitive property keys that must never leave the client.
 * Typed so callers and tests can carry them through the envelope without `any`.
 */
export interface SensitiveProps {
  width_mm?: number
  height_mm?: number
  depth_mm?: number
  sketch_url?: string
  sketch_data?: string
  sketch_content?: string
  image_url?: string
  image_data?: string
}

/**
 * Event property envelope — typed event name + redactable properties bag.
 * Every `AnalyticsEvent` satisfies this (typed keys are a subset of Record<string, unknown>),
 * and callers may add sensitive keys (dimensions, sketch, image) that redactProperties strips.
 */
export interface TrackEnvelope {
  name: AnalyticsEvent['name']
  properties: Record<string, unknown>
}

// ─── Redaction ──────────────────────────────────────────────────────────────

/** Keys whose values must never leave the client. */
const REDACTED_KEYS: Record<string, true> = {
  // Dimensions — too specific; could fingerprint a product
  width_mm: true,
  height_mm: true,
  depth_mm: true,
  // Sketch / image content — user-provided artwork
  sketch_url: true,
  sketch_data: true,
  sketch_content: true,
  image_url: true,
  image_data: true,
}

export type RedactedProperties = Record<string, unknown>

export function redactProperties(props: RedactedProperties): RedactedProperties {
  const result: RedactedProperties = {}
  for (const [key, value] of Object.entries(props)) {
    if (key in REDACTED_KEYS) {
      result[key] = '[REDACTED]'
    } else if (
      value !== null &&
      typeof value === 'object' &&
      !Array.isArray(value)
    ) {
      result[key] = redactProperties(value as RedactedProperties)
    } else {
      result[key] = value
    }
  }
  return result
}

// ─── Sink (provider adapter) ────────────────────────────────────────────────

export type AnalyticsSink = (event: AnalyticsEvent) => void

let sink: AnalyticsSink | null = null

export function registerSink(fn: AnalyticsSink): void {
  sink = fn
}

export function unregisterSink(): void {
  sink = null
}

// ─── track() ────────────────────────────────────────────────────────────────

/**
 * Emit an analytics event.
 *
 * 1. SSR guard  — returns silently when `window` is undefined.
 * 2. Consent gate — returns silently when consent is not 'granted'.
 * 3. Redaction   — dimensions and sketch fields are overwritten with '[REDACTED]'.
 * 4. Dispatch    — calls the registered sink (or silently drops).
 */
export function track(event: TrackEnvelope): void {
  if (typeof window === 'undefined') return

  if (getConsent() !== 'granted') return

  const safeEvent = {
    name: event.name,
    properties: redactProperties(event.properties),
  } as AnalyticsEvent

  sink?.(safeEvent)
}
