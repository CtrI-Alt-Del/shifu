import type { APIRequestContext } from '@playwright/test'

export type GamificationTransportObservation = {
  method: string
  path: string
  authorization: boolean
  cookie: boolean
  bffMark: boolean
  accountId: string
  status: number
}
export type ControlledRestResponses = Record<string, { status?: number; body: unknown }>

// Uses the same task-owned controlled upstream as the Mentor HTTP matrix.
// Identity and Better Auth stay real; only the selected response bodies are faked.
export const GamificationTransportFixture = (
  request: APIRequestContext,
  accountId: string,
) => {
  const port = process.env.SHIFU_MENTOR_STREAM_TEST_PROXY_PORT
  if (!port)
    throw new Error('Gamification transport requires the isolated opt-in upstream port')
  const controlURL = `http://127.0.0.1:${port}/__gamification-control/${accountId}`
  async function register(responses: ControlledRestResponses) {
    const response = await request.post(controlURL, { data: { responses } })
    if (!response.ok())
      throw new Error(
        `Could not configure Gamification upstream: HTTP ${response.status()}`,
      )
  }
  async function observations(): Promise<GamificationTransportObservation[]> {
    const response = await request.get(`${controlURL}/observations`)
    if (!response.ok()) throw new Error('Could not inspect Gamification upstream')
    return response.json()
  }
  async function dispose() {
    await request.delete(controlURL)
  }
  return { register, observations, dispose }
}
