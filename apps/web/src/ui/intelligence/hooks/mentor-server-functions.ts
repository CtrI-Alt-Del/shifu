import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { SERVER_ENV } from '@/constants/server-env'
import { AppError } from '@/core/errors/app-error'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { AxiosRestClient } from '@/rest/axios/axios-rest-client'
import { IntelligenceService } from '@/rest/services/intelligence-service'

type ScopedInput = { accountEmail: string }

async function getScopedService(accountEmail: string) {
  const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
  if (!access) {
    throw new AppError('Sua sessão expirou. Atualize a página.', 'Erro de autenticação')
  }
  if (access.email.toLocaleLowerCase() !== accountEmail.toLocaleLowerCase()) {
    throw new AppError('A sessão da conta mudou. Atualize a página.', 'Escopo alterado')
  }

  return {
    accessToken: access.accessToken,
    service: IntelligenceService(
      AxiosRestClient(SERVER_ENV.shifuServerAppUrl, { withCredentials: false }),
    ),
  }
}

export const listMentorSessionsServer = createServerFn({ method: 'GET' })
  .validator((data: ScopedInput & { search?: string; cursor?: string }) => data)
  .handler(async ({ data }) => {
    const { accessToken, service } = await getScopedService(data.accountEmail)
    return service.listMentorSessions(accessToken, {
      search: data.search,
      cursor: data.cursor,
    })
  })

export const getMentorSessionServer = createServerFn({ method: 'GET' })
  .validator((data: ScopedInput & { sessionId: string; cursor?: string }) => data)
  .handler(async ({ data }) => {
    const { accessToken, service } = await getScopedService(data.accountEmail)
    return service.getMentorSession(accessToken, data.sessionId, data.cursor)
  })

export const createMentorSessionServer = createServerFn({ method: 'POST' })
  .validator(
    (data: ScopedInput & { submissionKey: string; firstMessage: string }) => data,
  )
  .handler(async ({ data }) => {
    const { accessToken, service } = await getScopedService(data.accountEmail)
    return service.createMentorSession(accessToken, {
      submissionKey: data.submissionKey,
      firstMessage: data.firstMessage,
    })
  })

export const renameMentorSessionServer = createServerFn({ method: 'POST' })
  .validator((data: ScopedInput & { sessionId: string; title: string }) => data)
  .handler(async ({ data }) => {
    const { accessToken, service } = await getScopedService(data.accountEmail)
    return service.renameMentorSession(accessToken, data.sessionId, data.title)
  })

export const removeMentorSessionServer = createServerFn({ method: 'POST' })
  .validator((data: ScopedInput & { sessionId: string }) => data)
  .handler(async ({ data }) => {
    const { accessToken, service } = await getScopedService(data.accountEmail)
    return service.removeMentorSession(accessToken, data.sessionId)
  })
