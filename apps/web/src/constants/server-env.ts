import { z } from 'zod'

const SERVER_ENV_SCHEMA = z.object({
  shifuServerAppUrl: z.string().url().default('http://localhost:7777'),
})

const SERVER_ENV_INPUT = {
  // The FastAPI app is a single deployable serving Identity, Learning and
  // Intelligence alike; `SHIFU_IDENTITY_API_URL` is the existing name for its
  // base URL (set by `BetterAuthConfig`), reused here rather than introducing
  // a second env var for the same physical server.
  shifuServerAppUrl: process.env.SHIFU_IDENTITY_API_URL,
}

export const SERVER_ENV = SERVER_ENV_SCHEMA.parse(SERVER_ENV_INPUT)
