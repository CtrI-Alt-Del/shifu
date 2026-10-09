import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  createMentorSessionServer,
  getMentorSessionServer,
  listMentorSessionsServer,
  removeMentorSessionServer,
  renameMentorSessionServer,
} from '../mentor-server-functions'

const mocks = vi.hoisted(() => ({
  request: null as unknown,
  getCurrentAccess: vi.fn(),
  axiosRestClient: vi.fn(),
  intelligenceService: vi.fn(),
  service: {
    createMentorSession: vi.fn(),
    getMentorSession: vi.fn(),
    listMentorSessions: vi.fn(),
    removeMentorSession: vi.fn(),
    renameMentorSession: vi.fn(),
  },
}))

vi.mock('@tanstack/react-start', () => ({
  createServerFn: () => ({
    validator: (validate: (data: unknown) => unknown) => ({
      handler:
        (handler: (context: { data: unknown }) => Promise<unknown>) =>
        async (context: { data: unknown }) =>
          handler({ data: validate(context.data) }),
    }),
  }),
}))

vi.mock('@tanstack/react-start/server', () => ({
  getRequest: () => mocks.request,
}))

vi.mock('@/constants/server-env', () => ({
  SERVER_ENV: { shifuServerAppUrl: 'http://shifu.test' },
}))

vi.mock('@/provision/auth/better-auth/better-auth-provider', () => ({
  getBetterAuthProvider: () => ({ getCurrentAccess: mocks.getCurrentAccess }),
}))

vi.mock('@/rest/axios/axios-rest-client', () => ({
  AxiosRestClient: mocks.axiosRestClient,
}))

vi.mock('@/rest/services/intelligence-service', () => ({
  IntelligenceService: mocks.intelligenceService,
}))

describe('Mentor server functions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.request = new Request('http://shifu.test/intelligence')
    mocks.getCurrentAccess.mockResolvedValue({
      accessToken: 'access-token',
      email: 'Learner@example.test',
    })
    mocks.axiosRestClient.mockReturnValue({ restClient: true })
    mocks.intelligenceService.mockReturnValue(mocks.service)
    mocks.service.createMentorSession.mockResolvedValue({ session: { id: 'created' } })
    mocks.service.getMentorSession.mockResolvedValue({ session: { id: 'selected' } })
    mocks.service.listMentorSessions.mockResolvedValue({ items: [], nextCursor: null })
    mocks.service.removeMentorSession.mockResolvedValue(undefined)
    mocks.service.renameMentorSession.mockResolvedValue({ id: 'renamed' })
  })

  it('derives access from the request and forwards each scoped operation', async () => {
    const accountEmail = 'learner@EXAMPLE.test'
    const sessionId = '01J7T8AC91Z5K8M4JQ8C2D6F0B'
    const request = mocks.request

    await listMentorSessionsServer({
      data: { accountEmail, search: 'frações', cursor: 'sessions-cursor' },
    })
    await getMentorSessionServer({
      data: { accountEmail, sessionId, cursor: 'messages-cursor' },
    })
    await createMentorSessionServer({
      data: { accountEmail, submissionKey: 'submission-key', firstMessage: 'Pergunta.' },
    })
    await renameMentorSessionServer({
      data: { accountEmail, sessionId, title: 'Novo título' },
    })
    await removeMentorSessionServer({ data: { accountEmail, sessionId } })

    expect(mocks.getCurrentAccess).toHaveBeenCalledTimes(5)
    expect(mocks.getCurrentAccess).toHaveBeenCalledWith(request)
    expect(mocks.axiosRestClient).toHaveBeenCalledWith('http://shifu.test', {
      withCredentials: false,
    })
    expect(mocks.intelligenceService).toHaveBeenCalledTimes(5)
    expect(mocks.service.listMentorSessions).toHaveBeenCalledWith('access-token', {
      search: 'frações',
      cursor: 'sessions-cursor',
    })
    expect(mocks.service.getMentorSession).toHaveBeenCalledWith(
      'access-token',
      sessionId,
      'messages-cursor',
    )
    expect(mocks.service.createMentorSession).toHaveBeenCalledWith('access-token', {
      submissionKey: 'submission-key',
      firstMessage: 'Pergunta.',
    })
    expect(mocks.service.renameMentorSession).toHaveBeenCalledWith(
      'access-token',
      sessionId,
      'Novo título',
    )
    expect(mocks.service.removeMentorSession).toHaveBeenCalledWith(
      'access-token',
      sessionId,
    )
  })

  it('rejects requests without active access', async () => {
    mocks.getCurrentAccess.mockResolvedValueOnce(null)

    await expect(
      listMentorSessionsServer({ data: { accountEmail: 'learner@example.test' } }),
    ).rejects.toThrow('Sua sessão expirou. Atualize a página.')
    expect(mocks.intelligenceService).not.toHaveBeenCalled()
  })

  it('rejects a request when its account scope differs from current access', async () => {
    mocks.getCurrentAccess.mockResolvedValueOnce({
      accessToken: 'access-token',
      email: 'another@example.test',
    })

    await expect(
      listMentorSessionsServer({ data: { accountEmail: 'learner@example.test' } }),
    ).rejects.toThrow('A sessão da conta mudou. Atualize a página.')
    expect(mocks.intelligenceService).not.toHaveBeenCalled()
  })
})
