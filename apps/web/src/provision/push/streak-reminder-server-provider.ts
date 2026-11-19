import { getRequest } from '@tanstack/react-start/server'

import { HTTP_STATUS_CODE } from '@/constants/http-status-code'
import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import type { ServerFunctionFailure } from '@/core/shared/responses/server-function-failure'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { createServerRequestClient } from '@/rest/axios/server-request-client'
import { CommunicationService } from '@/rest/services/communication-service'
import { GamificationService } from '@/rest/services/gamification-service'

export type StreakReminderRequestResult<Value> =
  | { kind: 'ok'; value: Value }
  | ServerFunctionFailure

type StreakReminderRequestContext = {
  accessToken: string
  gamificationService: GamificationService
  communicationService: CommunicationService
}

// Runs one reminder request on the server with the learner's access token. When
// `accountEmail` is given, the session must still belong to that account.
const UNAUTHORIZED: ServerFunctionFailure = {
  kind: 'unauthorized',
  statusCode: HTTP_STATUS_CODE.unauthorized,
}
const INVALID: ServerFunctionFailure = {
  kind: 'invalid',
  statusCode: HTTP_STATUS_CODE.unprocessableEntity,
}
const UNAVAILABLE: ServerFunctionFailure = {
  kind: 'unavailable',
  statusCode: HTTP_STATUS_CODE.serviceUnavailable,
}

export async function runStreakReminderRequest<Value>(
  accountEmail: string | null,
  call: (context: StreakReminderRequestContext) => Promise<Value>,
): Promise<StreakReminderRequestResult<Value>> {
  try {
    const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
    if (!access) return UNAUTHORIZED
    if (
      accountEmail &&
      access.email.toLocaleLowerCase() !== accountEmail.toLocaleLowerCase()
    )
      return UNAUTHORIZED

    const restClient = createServerRequestClient(undefined)
    const value = await call({
      accessToken: access.accessToken,
      gamificationService: GamificationService(restClient),
      communicationService: CommunicationService(restClient),
    })
    return { kind: 'ok', value }
  } catch (error) {
    if (error instanceof AuthError)
      return error.kind === 'authentication-rejected' ? UNAUTHORIZED : UNAVAILABLE
    if (error instanceof RestError) {
      if (error.statusCode === HTTP_STATUS_CODE.unauthorized) return UNAUTHORIZED
      if (error.statusCode === HTTP_STATUS_CODE.unprocessableEntity) return INVALID
    }
    return UNAVAILABLE
  }
}
