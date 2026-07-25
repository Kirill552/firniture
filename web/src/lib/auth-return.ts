/**
 * Safe auth return URL validation and resolution logic.
 */

const ALLOWED_PATHS = ['/new', '/orders', '/bom', '/welcome']

/**
 * Validates whether a given URL is a safe, internal route.
 * Rejects absolute URLs, protocol-relative URLs (//), and unknown paths.
 */
export function isSafeReturnUrl(url: string | null | undefined): boolean {
  if (!url) return false

  let decoded = url
  try {
    decoded = decodeURIComponent(url)
  } catch {
    // Ignore decoding errors
  }

  // Reject protocol-relative URLs (e.g., //example.com) and absolute URLs
  if (decoded.startsWith('//') || decoded.includes('://')) {
    return false
  }

  // Extract the path before query parameters or hashes
  const path = decoded.split('?')[0].split('#')[0]

  // The path must match exactly one of the allowed paths
  return ALLOWED_PATHS.some((allowed) => path === allowed)
}

/**
 * Resolves the final destination path after token verification.
 */
export function resolveAuthReturnTarget(params: {
  isClaimed: boolean
  claimedOrderId?: string | null
  isNewUser: boolean
  returnTo?: string | null
}): string {
  // 1. If we successfully claimed a guest draft, go straight to that draft's BOM
  if (params.isClaimed && params.claimedOrderId) {
    return `/bom?orderId=${params.claimedOrderId}`
  }

  // 2. If this is a newly registered user, send them to onboarding welcome page
  if (params.isNewUser) {
    if (params.returnTo && isSafeReturnUrl(params.returnTo)) {
      return `/welcome?returnTo=${encodeURIComponent(params.returnTo)}`
    }
    return '/welcome'
  }

  // 3. Regular login: return to the verified safe return url, or default to orders
  if (params.returnTo && isSafeReturnUrl(params.returnTo)) {
    return params.returnTo
  }

  return '/orders'
}
