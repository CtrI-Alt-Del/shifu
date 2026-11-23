import { describe, expect, it, vi } from 'vitest'

import {
  getPendingConfirmationStatus,
  PENDING_COOKIE_NAME,
} from '../pending-confirmation-status'

const pendingRequest = (cookie = `${PENDING_COOKIE_NAME}=signed-context`) =>
  new Request('http://localhost:7000/', { headers: { cookie } })

describe('getPendingConfirmationStatus', () => {
  const cookieHeader = `tracking=value; ${PENDING_COOKIE_NAME}=signed-context; another=value`

  it.each(['', 'other=value', 'broken-cookie'])(
    'does not query auth when the pending cookie is absent (%s)',
    async (cookie) => {
      const handleAuthRequest = vi.fn()

      await expect(
        getPendingConfirmationStatus(pendingRequest(cookie), handleAuthRequest),
      ).resolves.toEqual({ state: 'delivery_issue', hasPendingContext: false })
      expect(handleAuthRequest).not.toHaveBeenCalled()
    },
  )

  it.each(['ready', 'cooldown', 'delivery_issue'] as const)(
    'returns a valid %s status',
    async (state) => {
      const handleAuthRequest = vi.fn(async () =>
        Response.json({ state, hasPendingContext: true }),
      )

      await expect(
        getPendingConfirmationStatus(pendingRequest(cookieHeader), handleAuthRequest),
      ).resolves.toEqual({ state, hasPendingContext: true })
      expect(handleAuthRequest).toHaveBeenCalledWith(
        expect.objectContaining({
          url: 'http://localhost:7000/api/auth/pending-confirmation',
          headers: expect.any(Headers),
        }),
      )
      expect(handleAuthRequest.mock.calls[0]?.[0].headers.get('cookie')).toBe(
        cookieHeader,
      )
    },
  )

  it('preserves a valid response without pending context', async () => {
    await expect(
      getPendingConfirmationStatus(pendingRequest(), async () =>
        Response.json({ state: 'delivery_issue', hasPendingContext: false }),
      ),
    ).resolves.toEqual({ state: 'delivery_issue', hasPendingContext: false })
  })

  it('reports an unavailable auth handler', async () => {
    await expect(
      getPendingConfirmationStatus(
        pendingRequest(),
        async () => new Response(null, { status: 503 }),
      ),
    ).rejects.toMatchObject({ kind: 'unavailable', statusCode: 503 })
  })

  it.each([
    null,
    [],
    { state: 'unknown', hasPendingContext: true },
    { state: 'ready', hasPendingContext: 'yes' },
  ])('rejects an invalid response body', async (body) => {
    await expect(
      getPendingConfirmationStatus(pendingRequest(), async () => Response.json(body)),
    ).rejects.toMatchObject({ kind: 'invalid-response' })
  })

  it('requires the exact cookie name', async () => {
    const handleAuthRequest = vi.fn()

    await getPendingConfirmationStatus(
      pendingRequest(`${PENDING_COOKIE_NAME}-unexpected=value`),
      handleAuthRequest,
    )

    expect(handleAuthRequest).not.toHaveBeenCalled()
  })
})
