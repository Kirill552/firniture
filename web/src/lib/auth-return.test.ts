import { describe, it, expect } from 'vitest'
import { isSafeReturnUrl, resolveAuthReturnTarget } from './auth-return'

describe('isSafeReturnUrl', () => {
  it('allows valid internal paths', () => {
    expect(isSafeReturnUrl('/new')).toBe(true)
    expect(isSafeReturnUrl('/orders')).toBe(true)
    expect(isSafeReturnUrl('/bom')).toBe(true)
    expect(isSafeReturnUrl('/welcome')).toBe(true)
  })

  it('allows valid internal paths with query parameters or hash', () => {
    expect(isSafeReturnUrl('/bom?orderId=123-456')).toBe(true)
    expect(isSafeReturnUrl('/new?entry=save-draft#step1')).toBe(true)
  })

  it('allows URL-encoded safe paths', () => {
    expect(isSafeReturnUrl('%2Fnew%3Fentry%3Dsave-draft')).toBe(true)
  })

  it('rejects protocol-relative URLs', () => {
    expect(isSafeReturnUrl('//evil-domain.com/new')).toBe(false)
    expect(isSafeReturnUrl('%2F%2Fevil-domain.com%2Fnew')).toBe(false)
  })

  it('rejects absolute URLs with protocol', () => {
    expect(isSafeReturnUrl('https://evil-domain.com/new')).toBe(false)
    expect(isSafeReturnUrl('http://localhost:3000/orders')).toBe(false)
  })

  it('rejects unknown internal paths', () => {
    expect(isSafeReturnUrl('/settings')).toBe(false)
    expect(isSafeReturnUrl('/arbitrary-path')).toBe(false)
  })

  it('handles null, undefined and empty inputs', () => {
    expect(isSafeReturnUrl(null)).toBe(false)
    expect(isSafeReturnUrl(undefined)).toBe(false)
    expect(isSafeReturnUrl('')).toBe(false)
  })
})

describe('resolveAuthReturnTarget', () => {
  it('returns BOM path directly if guest draft was claimed', () => {
    const target = resolveAuthReturnTarget({
      isClaimed: true,
      claimedOrderId: 'order-123',
      isNewUser: false,
      returnTo: '/new',
    })
    expect(target).toBe('/bom?orderId=order-123')
  })

  it('sends new user to onboarding welcome page and preserves safe returnTo', () => {
    const targetWithReturn = resolveAuthReturnTarget({
      isClaimed: false,
      isNewUser: true,
      returnTo: '/new',
    })
    expect(targetWithReturn).toBe('/welcome?returnTo=%2Fnew')

    const targetWithoutReturn = resolveAuthReturnTarget({
      isClaimed: false,
      isNewUser: true,
      returnTo: null,
    })
    expect(targetWithoutReturn).toBe('/welcome')
  })

  it('returns validated returnTo URL for regular login', () => {
    const targetSafe = resolveAuthReturnTarget({
      isClaimed: false,
      isNewUser: false,
      returnTo: '/new?entry=save',
    })
    expect(targetSafe).toBe('/new?entry=save')

    const targetUnsafe = resolveAuthReturnTarget({
      isClaimed: false,
      isNewUser: false,
      returnTo: 'https://evil.com/malicious',
    })
    expect(targetUnsafe).toBe('/orders')
  })

  it('defaults to /orders if returnTo is missing', () => {
    const target = resolveAuthReturnTarget({
      isClaimed: false,
      isNewUser: false,
      returnTo: null,
    })
    expect(target).toBe('/orders')
  })
})
