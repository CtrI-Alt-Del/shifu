import { useQuery } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { serverFunctionTelemetryMiddleware } from '@/start'
import { getRequest } from '@tanstack/react-start/server'

import { HTTP_STATUS_CODE } from '@/constants/http-status-code'
import { SERVER_ENV } from '@/constants/server-env'
import type { RequestTelemetryContext } from '@/core/shared/interfaces/request-telemetry-context'
import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import type { PracticeCalendar } from '@/core/gamification/practice-calendar'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { createServerRequestClient } from '@/rest/axios/server-request-client'
import { GamificationService } from '@/rest/services/gamification-service'

type PracticeCalendarResult =
  | { kind: 'success'; calendar: PracticeCalendar }
  | { kind: 'unauthorized' | 'forbidden' | 'unavailable'; statusCode?: number }

const getPracticeCalendar = createServerFn({ method: 'GET' })
  .middleware([serverFunctionTelemetryMiddleware])
  .validator((input: { year: number; month: number }) => input)
  .handler(
    async ({
      data,
      context,
    }: {
      data: { year: number; month: number }
      context: RequestTelemetryContext
    }): Promise<PracticeCalendarResult> => {
      try {
        const access = await getBetterAuthProvider().getCurrentAccess(
          getRequest(),
          context.requestId,
        )
        if (!access) return { kind: 'unauthorized' }

        const gamificationService = GamificationService(
          createServerRequestClient(context, { baseUrl: SERVER_ENV.shifuServerAppUrl }),
        )
        const calendar = await gamificationService.getPracticeCalendar(
          access.accessToken,
          data.year,
          data.month,
        )
        return { kind: 'success', calendar }
      } catch (error) {
        if (error instanceof AuthError) {
          return error.kind === 'authentication-rejected'
            ? { kind: 'unauthorized', statusCode: error.statusCode }
            : { kind: 'unavailable', statusCode: error.statusCode }
        }

        if (error instanceof RestError) {
          if (error.statusCode === HTTP_STATUS_CODE.unauthorized)
            return { kind: 'unauthorized' }
          if (error.statusCode === HTTP_STATUS_CODE.forbidden)
            return { kind: 'forbidden' }
          return { kind: 'unavailable', statusCode: error.statusCode }
        }

        return { kind: 'unavailable' }
      }
    },
  )

export function usePracticeCalendarQuery(year: number | null, month: number | null) {
  const query = useQuery({
    queryKey: ['gamification', 'practice-calendar', year, month],
    enabled: year !== null && month !== null,
    retry: false,
    queryFn: async () => {
      const result = await getPracticeCalendar({
        data: { year: year as number, month: month as number },
      })

      if (result.kind === 'success') return result.calendar
      if (result.kind === 'unauthorized' || result.kind === 'forbidden') {
        throw new AuthError('authentication-rejected', 'Sua sessão expirou.', {
          statusCode: result.statusCode,
        })
      }
      throw new RestError(
        'Serviço temporariamente indisponível.',
        result.statusCode ?? 503,
      )
    },
  })

  return {
    calendar: query.data ?? null,
    calendarError: query.error ?? null,
    isLoadingCalendar: query.isPending,
    isFetchingCalendar: query.isFetching,
    refetchCalendar: query.refetch,
  }
}
