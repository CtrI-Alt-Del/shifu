import { useInfiniteQuery } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { serverFunctionTelemetryMiddleware } from '@/start'
import { getRequest } from '@tanstack/react-start/server'
import { useEffect, useState } from 'react'

import { SERVER_ENV } from '@/constants/server-env'
import { AppError } from '@/core/errors/app-error'
import type { RequestTelemetryContext } from '@/core/shared/interfaces/request-telemetry-context'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { createServerRequestClient } from '@/rest/axios/server-request-client'
import { LearningService } from '@/rest/services/learning-service'

const SEARCH_DEBOUNCE_MS = 300
const PAGE_SIZE = 20

const searchSkillCatalog = createServerFn({ method: 'GET' })
  .middleware([serverFunctionTelemetryMiddleware])
  .validator((data: { goalId: string; query?: string; cursor?: string }) => data)
  .handler(
    async ({
      data,
      context,
    }: {
      data: { goalId: string; query?: string; cursor?: string }
      context: RequestTelemetryContext
    }) => {
      const access = await getBetterAuthProvider().getCurrentAccess(
        getRequest(),
        context.requestId,
      )
      if (!access) {
        throw new AppError(
          'Sua sessão expirou. Atualize a página.',
          'Erro de autenticação',
        )
      }

      const learningService = LearningService(
        createServerRequestClient(context, { baseUrl: SERVER_ENV.shifuServerAppUrl }),
      )
      return learningService.searchSkillCatalog(access.accessToken, data.goalId, {
        query: data.query,
        cursor: data.cursor,
        limit: PAGE_SIZE,
      })
    },
  )

export function useSkillCatalogQuery(goalId: string) {
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query), SEARCH_DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [query])

  const { data, error, isLoading, isFetchingNextPage, hasNextPage, fetchNextPage } =
    useInfiniteQuery({
      queryKey: ['learning', 'skill-catalog', goalId, debouncedQuery],
      queryFn: ({ pageParam }: { pageParam: string | undefined }) =>
        searchSkillCatalog({
          data: { goalId, query: debouncedQuery || undefined, cursor: pageParam },
        }),
      initialPageParam: undefined as string | undefined,
      getNextPageParam: (lastPage) => lastPage.nextCursor ?? undefined,
    })

  const skills = data?.pages.flatMap((page) => page.items) ?? []

  return {
    skills,
    skillsError: error,
    isLoadingSkills: isLoading,
    isLoadingMoreSkills: isFetchingNextPage,
    hasMoreSkills: !!hasNextPage,
    loadMoreSkills: fetchNextPage,
    setSkillCatalogQuery: setQuery,
  }
}
