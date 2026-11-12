import { HTTP_STATUS_CODE } from '@/constants/http-status-code'
import { RestError } from '@/core/errors/rest-error'
import {
  AI_QUOTA_EXHAUSTED_CODE,
  type MentorStartResult,
} from '@/core/intelligence/ai-quota-usage'

/**
 * Server functions do not serialize `RestError`, so a quota refusal travels as typed
 * data. Every other failure keeps being thrown.
 */
export async function toMentorStartResult<Value>(
  operation: () => Promise<Value>,
): Promise<MentorStartResult<Value>> {
  try {
    return { ok: true, value: await operation() }
  } catch (error) {
    if (
      error instanceof RestError &&
      error.statusCode === HTTP_STATUS_CODE.tooManyRequests &&
      error.code === AI_QUOTA_EXHAUSTED_CODE
    )
      return { ok: false, failure: { kind: 'quota-exhausted' } }
    throw error
  }
}
