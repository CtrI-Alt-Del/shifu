import { expect, test } from '../playwright'

test.describe('same-origin registration confirmation auth handlers', () => {
  test('creates a pending handoff and preserves its cooldown through the BFF', async ({
    request,
  }, testInfo) => {
    const email = `registration-handler-${testInfo.parallelIndex}-${testInfo.retry}@shifu.local`
    const registration = await request.post('/api/auth/register/identity', {
      data: {
        displayName: 'Registration Handler Learner',
        email,
        password: 'shifu-test-password',
      },
    })

    expect(registration.status()).toBe(200)
    expect(await registration.json()).toEqual({ redirectTo: '/pending-confirmation' })
    expect(registration.headers()['set-cookie']).toMatch(
      /shifu-pending-flow=[^;]+; Path=\//,
    )

    const status = await request.get('/api/auth/pending-confirmation')

    expect(status.status()).toBe(200)
    const statusBody = await status.json()
    expect(statusBody).toEqual({
      state: 'cooldown',
      retryAfterSeconds: expect.any(Number),
    })
    expect(statusBody.retryAfterSeconds).toBeGreaterThan(0)
    expect(statusBody.retryAfterSeconds).toBeLessThanOrEqual(60)

    const resend = await request.post('/api/auth/pending-confirmation/resend')

    expect(resend.status()).toBe(200)
    const resendBody = await resend.json()
    expect(resendBody).toEqual({
      result: 'cooldown',
      retryAfterSeconds: expect.any(Number),
    })
    expect(resendBody.retryAfterSeconds).toBeGreaterThan(0)
    expect(resendBody.retryAfterSeconds).toBeLessThanOrEqual(60)
  })

  test('maps an unknown confirmation token through the registered BFF handler', async ({
    request,
  }) => {
    const response = await request.post('/api/auth/confirm-email', {
      data: { token: 'A'.repeat(43) },
    })

    expect(response.status()).toBe(200)
    expect(await response.json()).toEqual({ result: 'invalid', redirectTo: '/login' })
    expect(response.headers()['set-cookie'] ?? '').not.toContain(
      'better-auth.session_token=',
    )
  })
})
