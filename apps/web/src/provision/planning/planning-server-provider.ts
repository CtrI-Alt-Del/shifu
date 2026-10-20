import { HTTP_STATUS_CODE } from '@/constants/http-status-code'
import { SERVER_ENV } from '@/constants/server-env'
import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import type { PlanningFailure } from '@/core/intelligence/planning-session'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { AxiosRestClient } from '@/rest/axios/axios-rest-client'
import { IntelligenceService } from '@/rest/services/intelligence-service'

type PlanningOperation<Result> = (
  service: IntelligenceService,
  accessToken: string,
) => Promise<Result>

export async function withPlanningService<Result>(
  request: Request,
  operation: PlanningOperation<Result>,
): Promise<Result | PlanningFailure> {
  try {
    const access = await getBetterAuthProvider().getCurrentAccess(request)
    if (!access) return { kind: 'unauthorized' }

    const service = IntelligenceService(
      AxiosRestClient(SERVER_ENV.shifuServerAppUrl, { withCredentials: false }),
    )
    return await operation(service, access.accessToken)
  } catch (error) {
    return planningFailure(error)
  }
}

export function planningFailure(error: unknown): PlanningFailure {
  if (error instanceof AuthError) {
    return error.kind === 'unavailable'
      ? { kind: 'unavailable' }
      : { kind: 'unauthorized' }
  }
  if (error instanceof RestError) {
    if (error.statusCode === HTTP_STATUS_CODE.unauthorized)
      return { kind: 'unauthorized' }
    if (error.statusCode === HTTP_STATUS_CODE.notFound) return { kind: 'not-found' }
    if (error.statusCode === HTTP_STATUS_CODE.conflict) {
      return { kind: 'conflict', message: error.message }
    }
    if (
      error.statusCode === HTTP_STATUS_CODE.badRequest ||
      error.statusCode === HTTP_STATUS_CODE.unprocessableEntity
    ) {
      return { kind: 'invalid-request', message: error.message }
    }
  }
  return { kind: 'unavailable' }
}
