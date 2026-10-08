import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import type { AchievementsOverview } from '@/core/gamification/achievements-overview'
import { HTTP_STATUS_CODE } from '@/constants/http-status-code'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { AchievementsProvider } from '@/provision/gamification/achievements-provider'

export type AchievementsResult =
  | { kind: 'success'; overview: AchievementsOverview }
  | {
      kind: 'unauthorized' | 'forbidden' | 'unavailable'
      statusCode?: number
    }

export const getAchievements = createServerFn({ method: 'GET' }).handler(
  async (): Promise<AchievementsResult> => {
    try {
      const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
      if (!access) return { kind: 'unauthorized' }

      const overview = await AchievementsProvider().getAchievements(access.accessToken)
      return { kind: 'success', overview }
    } catch (error) {
      if (error instanceof AuthError) {
        return error.kind === 'authentication-rejected'
          ? { kind: 'unauthorized', statusCode: error.statusCode }
          : { kind: 'unavailable', statusCode: error.statusCode }
      }

      if (error instanceof RestError) {
        if (error.statusCode === HTTP_STATUS_CODE.unauthorized)
          return { kind: 'unauthorized' }
        if (error.statusCode === HTTP_STATUS_CODE.forbidden) return { kind: 'forbidden' }
        return { kind: 'unavailable', statusCode: error.statusCode }
      }

      return { kind: 'unavailable' }
    }
  },
)
