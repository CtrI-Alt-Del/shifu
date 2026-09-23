import { useInfiniteQuery } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'
import { useEffect, useState } from 'react'

import { SERVER_ENV } from '@/constants/server-env'
import { AppError } from '@/core/errors/app-error'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { AxiosRestClient } from '@/rest/axios/axios-rest-client'
import { LearningService } from '@/rest/services/learning-service'

const SEARCH_DEBOUNCE_MS = 300
const PAGE_SIZE = 20

const searchSkillCatalog = createServerFn({ method: 'GET' })
  .validator((data: { goalId: string; query?: string; cursor?: string }) => data)
  .handler(async ({ data }) => {
    const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
    if (!access) {
      throw new AppError('Sua sessão expirou. Atualize a página.', 'Erro de autenticação')
    }

    const learningService = LearningService(
      AxiosRestClient(SERVER_ENV.shifuServerAppUrl, { withCredentials: false }),
    )
    return learningService.searchSkillCatalog(access.accessToken, data.goalId, {
      query: data.query,
      cursor: data.cursor,
      limit: PAGE_SIZE,
    })
  })

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
