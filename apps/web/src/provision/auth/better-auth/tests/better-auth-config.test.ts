import { afterEach, describe, expect, it, vi } from 'vitest'

import { readTrustedOrigins } from '../better-auth-config'

describe('readTrustedOrigins', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it('trusts the other loopback spelling in development', () => {
    vi.stubEnv('NODE_ENV', 'development')

    expect(readTrustedOrigins('http://localhost:7000')).toEqual(['http://127.0.0.1:7000'])
    expect(readTrustedOrigins('http://127.0.0.1:7000')).toEqual(['http://localhost:7000'])
  })

  it('adds nothing for a public host or in production', () => {
    vi.stubEnv('NODE_ENV', 'development')
    expect(readTrustedOrigins('https://shifu.example.com')).toEqual([])

    vi.stubEnv('NODE_ENV', 'production')
    expect(readTrustedOrigins('http://localhost:7000')).toEqual([])
  })
})
