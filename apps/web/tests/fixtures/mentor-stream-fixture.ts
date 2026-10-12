import { createHash } from 'node:crypto'
import type { APIRequestContext } from '@playwright/test'
import { Pool } from 'pg'
import { buildMentorResponseEventsPath } from '../../src/constants/routes'
import type { SignInHandlerAccount } from './identity-module-fixture'

export type MentorStreamObservations = {
  calls: number
  cancelCalls: number
  closed: boolean
  ended: boolean
  upstreamAuthorization: boolean
  upstreamCookie: boolean
  cursor: string | null
  authorizedAccount: string | null
}
export const MentorStreamFixture = (
  request: APIRequestContext,
  account: SignInHandlerAccount,
  testId: string,
) => {
  const port = process.env.SHIFU_MENTOR_STREAM_TEST_PROXY_PORT
  if (!port)
    throw new Error(
      'CI-15 requires SHIFU_MENTOR_STREAM_TEST_PROXY_PORT and a task-owned isolated runtime',
    )
  const hash = BigInt(`0x${createHash('sha256').update(testId).digest('hex')}`)
  const sessionId = `01MT${String(hash % 10n ** 22n).padStart(22, '0')}`
  const controlURL = `http://127.0.0.1:${port}/__mentor-control/${sessionId}`
  async function register(
    input: {
      initialChunk?: string
      finalChunk?: string
      status?: number
      ownerAccountId?: string
    } = {},
  ) {
    const response = await request.post(controlURL, {
      data: { ownerAccountId: account.accountId, ...input },
    })
    if (!response.ok()) throw new Error('Could not configure the controlled upstream')
  }
  async function observations(): Promise<MentorStreamObservations> {
    const response = await request.get(`${controlURL}/observations`)
    if (!response.ok()) throw new Error('Could not read upstream observations')
    return response.json()
  }
  async function release() {
    await request.post(`${controlURL}/release`)
  }
  async function dispose() {
    await request.delete(controlURL)
  }
  async function changeAccountAccess(mode: 'expire' | 'revoke') {
    const databaseURL = process.env.BETTER_AUTH_DATABASE_URL
    if (!databaseURL)
      throw new Error(
        'The CI-15 access fixture requires an explicitly isolated auth database',
      )
    const pool = new Pool({ connectionString: databaseURL })
    try {
      if (mode === 'expire')
        await pool.query(
          "update better_auth_sessions set expires_at = now() - interval '1 minute' where user_id = $1",
          [account.accountId],
        )
      else
        await pool.query(
          'update identity_accounts set access_version = access_version + 1 where id = $1',
          [account.accountId],
        )
    } finally {
      await pool.end()
    }
  }
  return {
    sessionId,
    path: buildMentorResponseEventsPath(sessionId),
    register,
    observations,
    release,
    dispose,
    changeAccountAccess,
  }
}
