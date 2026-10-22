import { expect, test } from '../playwright'

const VALID_REQUEST_ID = '123e4567-e89b-42d3-a456-426614174000'

test.describe('structured telemetry HTTP correlation', () => {
  test('retains a valid request ID and generates one for malformed input', async ({
    request,
  }) => {
    const retained = await request.get('/api/auth/get-session', {
      headers: { 'X-Request-ID': VALID_REQUEST_ID },
    })
    expect(retained.status()).toBe(200)
    expect(retained.headers()['x-request-id']).toBe(VALID_REQUEST_ID)

    const generated = await request.get('/api/auth/get-session', {
      headers: { 'X-Request-ID': 'password=secret-token' },
    })
    expect(generated.status()).toBe(200)
    const generatedRequestId = generated.headers()['x-request-id']
    expect(generatedRequestId).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
    )
    expect(generatedRequestId).not.toContain('secret-token')
  })

  test('keeps the same correlation ID across the authenticated BFF-to-API boundary', async ({
    authenticatedPage,
  }) => {
    await authenticatedPage.setExtraHTTPHeaders({
      'X-Request-ID': VALID_REQUEST_ID,
    })

    const response = await authenticatedPage.goto('/')

    expect(response?.status()).toBe(200)
    expect(response?.headers()['x-request-id']).toBe(VALID_REQUEST_ID)
  })
})
