import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createMentorSessionServer } from '../use-create-mentor-session-action'
import { createMentorAttachmentBatchServer } from '../use-create-mentor-attachment-batch-action'
import { getMentorSessionServer } from '../use-mentor-session-query'
import { listMentorSessionsServer } from '../use-mentor-sessions-query'
import { removeMentorSessionServer } from '../use-remove-mentor-session-action'
import { renameMentorSessionServer } from '../use-rename-mentor-session-action'
import { submitMentorMessageServer } from '../use-submit-mentor-message-action'
import { editLearnerMemoryServer } from '../../widgets/pages/memories-page/use-edit-learner-memory-action'
import { listLearnerMemoriesServer } from '../../widgets/pages/memories-page/use-learner-memories-query'
import { getLearnerMemoryServer } from '../../widgets/pages/memories-page/use-learner-memory-query'
import { removeLearnerMemoryServer } from '../../widgets/pages/memories-page/use-remove-learner-memory-action'
import { RestError } from '@/core/errors/rest-error'
import type { RestClient } from '@/core/shared/interfaces/rest-client'
import { RestResponse } from '@/core/shared/responses/rest-response'

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
    submitMentorMessage: vi.fn(),
    listLearnerMemories: vi.fn(),
    getLearnerMemory: vi.fn(),
    editLearnerMemory: vi.fn(),
    removeLearnerMemory: vi.fn(),
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

vi.mock('@/rest/fetch/fetch-rest-stream-client', () => ({
  FetchRestStreamClient: () => ({ getStream: vi.fn() }),
}))

vi.mock('@/rest/services/intelligence-service', () => ({
  IntelligenceService: mocks.intelligenceService,
}))

describe('Mentor server functions', () => {
  beforeEach(() => {
    vi.resetAllMocks()
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
    mocks.service.submitMentorMessage.mockResolvedValue({ session: { id: 'updated' } })
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
      data: {
        accountEmail,
        submissionKey: 'e9cfaab2-fb57-40e6-96aa-e6d7afdd7259',
        firstMessage: 'Pergunta.',
      },
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
      submissionKey: 'e9cfaab2-fb57-40e6-96aa-e6d7afdd7259',
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

  it('maps response attachment sources through the scoped session query', async () => {
    const { IntelligenceService: createIntelligenceService } = await vi.importActual<
      typeof import('@/rest/services/intelligence-service')
    >('@/rest/services/intelligence-service')
    const sessionDetail = {
      session: {
        id: '01J7T8AC91Z5K8M4JQ8C2D6F0B',
        title: 'Dúvida sobre leitura',
        created_at: '2026-10-14T10:00:00Z',
        updated_at: '2026-10-14T10:01:00Z',
        last_activity_at: '2026-10-14T10:01:00Z',
      },
      messages: { items: [], next_cursor: null },
      pending_learner_message_id: null,
      response: {
        attempt_id: '01J7T8AC91Z5K8M4JQ8C2D6F0C',
        learner_message_id: '01J7T8AC91Z5K8M4JQ8C2D6F0D',
        status: 'completed',
        blocks: [
          {
            block_key: 'answer-1',
            ordinal: 1,
            intent: 'explain_concept',
            content: 'A imagem mostra uma fração.',
            sources: [
              {
                attachment_id: '01J7T8AC91Z5K8M4JQ8C2D6F0E',
                chunk_id: 'chunk-1',
                page_number: 2,
                locator: 'x:10,y:20',
              },
            ],
          },
        ],
        consultations: [],
        last_sequence: 4,
        failure_code: null,
      },
    }
    const get = vi
      .fn()
      .mockResolvedValue(new RestResponse({ body: sessionDetail, statusCode: 200 }))
    const restClient = { get } as unknown as RestClient
    mocks.axiosRestClient.mockReturnValue(restClient)
    mocks.intelligenceService.mockImplementation((client: RestClient) =>
      createIntelligenceService(client),
    )
    const sessionId = '01J7T8AC91Z5K8M4JQ8C2D6F0B'

    const detail = await getMentorSessionServer({
      data: {
        accountEmail: 'learner@example.test',
        sessionId,
        cursor: 'messages-cursor',
      },
    })

    expect(get).toHaveBeenCalledWith(`/intelligence/mentor-sessions/${sessionId}`, {
      headers: {
        Authorization: 'Bearer access-token',
        'Cache-Control': 'no-store',
      },
      params: { cursor: 'messages-cursor' },
    })
    expect(detail.response?.blocks[0]?.sources).toEqual([
      {
        attachmentId: '01J7T8AC91Z5K8M4JQ8C2D6F0E',
        chunkId: 'chunk-1',
        pageNumber: 2,
        locator: 'x:10,y:20',
      },
    ])
  })

  it('creates an attachment batch through the scoped server function and REST adapter', async () => {
    const { IntelligenceService: createIntelligenceService } = await vi.importActual<
      typeof import('@/rest/services/intelligence-service')
    >('@/rest/services/intelligence-service')
    const sessionId = '01J7T8AC91Z5K8M4JQ8C2D6F0B'
    const batchId = '01J7T8AC91Z5K8M4JQ8C2D6F0C'
    const post = vi.fn().mockResolvedValue(
      new RestResponse({
        body: { batch_id: batchId, expires_at: '2026-10-14T10:15:00Z', attachments: [] },
        statusCode: 201,
      }),
    )
    const restClient = { post } as unknown as RestClient
    mocks.axiosRestClient.mockReturnValue(restClient)
    mocks.intelligenceService.mockImplementation((client: RestClient) =>
      createIntelligenceService(client),
    )

    const batch = await createMentorAttachmentBatchServer({
      data: { accountEmail: 'learner@example.test', sessionId },
    })

    expect(batch).toEqual({
      batchId,
      expiresAt: '2026-10-14T10:15:00Z',
      attachments: [],
    })
    expect(post).toHaveBeenCalledWith(
      '/intelligence/mentor-attachment-batches',
      { session_id: sessionId },
      {
        headers: {
          Authorization: 'Bearer access-token',
          'Cache-Control': 'no-store',
        },
      },
    )
  })

  it('propagates an attachment batch conflict through the scoped server function', async () => {
    const { IntelligenceService: createIntelligenceService } = await vi.importActual<
      typeof import('@/rest/services/intelligence-service')
    >('@/rest/services/intelligence-service')
    const post = vi
      .fn()
      .mockResolvedValue(
        new RestResponse({ statusCode: 409, errorMessage: 'Batch is not ready.' }),
      )
    const restClient = { post } as unknown as RestClient
    mocks.axiosRestClient.mockReturnValue(restClient)
    mocks.intelligenceService.mockImplementation((client: RestClient) =>
      createIntelligenceService(client),
    )

    await expect(
      createMentorAttachmentBatchServer({
        data: { accountEmail: 'learner@example.test' },
      }),
    ).rejects.toThrow('Batch is not ready.')
    expect(post).toHaveBeenCalledOnce()
  })

  it('forwards attachment selections through scoped session creation and submission', async () => {
    const { IntelligenceService: createIntelligenceService } = await vi.importActual<
      typeof import('@/rest/services/intelligence-service')
    >('@/rest/services/intelligence-service')
    const sessionId = '01J7T8AC91Z5K8M4JQ8C2D6F0B'
    const batchId = '01J7T8AC91Z5K8M4JQ8C2D6F0C'
    const attachmentIds = ['01J7T8AC91Z5K8M4JQ8C2D6F0D']
    const detail = {
      session: {
        id: sessionId,
        title: 'Dúvida sobre leitura',
        created_at: '2026-10-14T10:00:00Z',
        updated_at: '2026-10-14T10:01:00Z',
        last_activity_at: '2026-10-14T10:01:00Z',
      },
      messages: { items: [], next_cursor: null },
      pending_learner_message_id: null,
      response: null,
    }
    const post = vi
      .fn()
      .mockResolvedValue(new RestResponse({ body: detail, statusCode: 202 }))
    const restClient = { post } as unknown as RestClient
    mocks.axiosRestClient.mockReturnValue(restClient)
    mocks.intelligenceService.mockImplementation((client: RestClient) =>
      createIntelligenceService(client),
    )
    const submissionKey = 'e9cfaab2-fb57-40e6-96aa-e6d7afdd7259'

    const created = await createMentorSessionServer({
      data: {
        accountEmail: 'learner@example.test',
        submissionKey,
        firstMessage: 'Explique esta imagem.',
        attachmentBatchId: batchId,
        attachmentIds,
      },
    })
    const submitted = await submitMentorMessageServer({
      data: {
        accountEmail: 'learner@example.test',
        sessionId,
        submissionKey,
        content: 'E esta outra parte?',
        contextHint: null,
        attachmentBatchId: batchId,
        attachmentIds,
      },
    })

    expect(created.session.id).toBe(sessionId)
    expect(submitted.session.id).toBe(sessionId)
    expect(post).toHaveBeenNthCalledWith(
      1,
      '/intelligence/mentor-sessions',
      {
        submission_key: submissionKey,
        first_message: 'Explique esta imagem.',
        attachment_batch_id: batchId,
        attachment_ids: attachmentIds,
      },
      {
        headers: {
          Authorization: 'Bearer access-token',
          'Cache-Control': 'no-store',
        },
      },
    )
    expect(post).toHaveBeenNthCalledWith(
      2,
      `/intelligence/mentor-sessions/${sessionId}/messages`,
      {
        submission_key: submissionKey,
        content: 'E esta outra parte?',
        context_hint: null,
        attachment_batch_id: batchId,
        attachment_ids: attachmentIds,
      },
      {
        headers: {
          Authorization: 'Bearer access-token',
          'Cache-Control': 'no-store',
        },
      },
    )
  })

  it('rejects a session with attachment ids that lack a batch before service access', async () => {
    await expect(
      createMentorSessionServer({
        data: {
          accountEmail: 'learner@example.test',
          submissionKey: 'e9cfaab2-fb57-40e6-96aa-e6d7afdd7259',
          firstMessage: 'Explique esta imagem.',
          attachmentIds: ['01J7T8AC91Z5K8M4JQ8C2D6F0E'],
        },
      }),
    ).rejects.toThrow()
    expect(mocks.getCurrentAccess).not.toHaveBeenCalled()
    expect(mocks.service.createMentorSession).not.toHaveBeenCalled()
  })

  it('rejects a message with attachment ids that lack a batch before service access', async () => {
    await expect(
      submitMentorMessageServer({
        data: {
          accountEmail: 'learner@example.test',
          sessionId: '01J7T8AC91Z5K8M4JQ8C2D6F0B',
          submissionKey: 'e9cfaab2-fb57-40e6-96aa-e6d7afdd7259',
          content: 'Explique esta imagem.',
          contextHint: null,
          attachmentIds: ['01J7T8AC91Z5K8M4JQ8C2D6F0E'],
        },
      }),
    ).rejects.toThrow()
    expect(mocks.getCurrentAccess).not.toHaveBeenCalled()
    expect(mocks.service.submitMentorMessage).not.toHaveBeenCalled()
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

describe('Learner memory server functions', () => {
  const accountEmail = 'Learner@example.test'
  const memoryId = '01J7T8AC91Z5K8M4JQ8C2D6F0B'

  beforeEach(() => {
    vi.resetAllMocks()
    mocks.request = new Request('http://shifu.test/intelligence/memories')
    mocks.getCurrentAccess.mockResolvedValue({
      accessToken: 'access-token',
      email: 'Learner@example.test',
    })
    mocks.axiosRestClient.mockReturnValue({ restClient: true })
    mocks.intelligenceService.mockReturnValue(mocks.service)
  })

  it('derives access from the request and forwards each scoped memory operation', async () => {
    mocks.service.listLearnerMemories.mockResolvedValue([])
    mocks.service.getLearnerMemory.mockResolvedValue({ id: memoryId })
    mocks.service.editLearnerMemory.mockResolvedValue({ id: memoryId, version: 2 })
    mocks.service.removeLearnerMemory.mockResolvedValue(undefined)

    const list = await listLearnerMemoriesServer({
      data: { accountEmail, q: 'python', category: 'declared_knowledge' },
    })
    const read = await getLearnerMemoryServer({ data: { accountEmail, memoryId } })
    const edited = await editLearnerMemoryServer({
      data: { accountEmail, memoryId, content: 'Novo texto.', expectedVersion: 1 },
    })
    const removed = await removeLearnerMemoryServer({ data: { accountEmail, memoryId } })

    expect(mocks.getCurrentAccess).toHaveBeenCalledTimes(4)
    expect(mocks.getCurrentAccess).toHaveBeenCalledWith(mocks.request)
    expect(mocks.axiosRestClient).toHaveBeenCalledWith('http://shifu.test', {
      withCredentials: false,
    })
    expect(mocks.service.listLearnerMemories).toHaveBeenCalledWith('access-token', {
      q: 'python',
      category: 'declared_knowledge',
    })
    expect(mocks.service.getLearnerMemory).toHaveBeenCalledWith('access-token', memoryId)
    expect(mocks.service.editLearnerMemory).toHaveBeenCalledWith(
      'access-token',
      memoryId,
      { content: 'Novo texto.', expectedVersion: 1 },
    )
    expect(mocks.service.removeLearnerMemory).toHaveBeenCalledWith(
      'access-token',
      memoryId,
    )
    expect(list).toEqual([])
    expect(read).toEqual({ kind: 'ok', memory: { id: memoryId } })
    expect(edited).toEqual({ kind: 'ok', memory: { id: memoryId, version: 2 } })
    expect(removed).toEqual({ kind: 'ok' })
  })

  it('rejects an account that differs from the request session', async () => {
    await expect(
      listLearnerMemoriesServer({ data: { accountEmail: 'other@example.test' } }),
    ).rejects.toThrow('A sessão da conta mudou')
    expect(mocks.service.listLearnerMemories).not.toHaveBeenCalled()
  })

  it.each([
    ['an unknown key', { accountEmail, extra: true }],
    ['an invalid category', { accountEmail, category: 'all' }],
    ['a query over 100 characters', { accountEmail, q: 'a'.repeat(101) }],
    ['an invalid account email', { accountEmail: 'not-an-email' }],
  ])('rejects the list input with %s', async (_description, data) => {
    await expect(
      listLearnerMemoriesServer({ data: data as { accountEmail: string } }),
    ).rejects.toThrow()
    expect(mocks.service.listLearnerMemories).not.toHaveBeenCalled()
  })

  it.each([
    ['a malformed id', { accountEmail, memoryId: 'not-a-ulid' }],
    ['an unknown key', { accountEmail, memoryId, extra: true }],
  ])('rejects the get input with %s', async (_description, data) => {
    await expect(getLearnerMemoryServer({ data })).rejects.toThrow()
    expect(mocks.service.getLearnerMemory).not.toHaveBeenCalled()
  })

  it.each([
    ['a malformed id', { accountEmail, memoryId: 'x', content: 'a', expectedVersion: 1 }],
    ['a zero version', { accountEmail, memoryId, content: 'a', expectedVersion: 0 }],
    [
      'a fractional version',
      { accountEmail, memoryId, content: 'a', expectedVersion: 1.5 },
    ],
    ['a missing content', { accountEmail, memoryId, expectedVersion: 1 }],
  ])('rejects the edit input with %s', async (_description, data) => {
    await expect(editLearnerMemoryServer({ data: data as never })).rejects.toThrow()
    expect(mocks.service.editLearnerMemory).not.toHaveBeenCalled()
  })

  it('rejects the delete input with a malformed id', async () => {
    await expect(
      removeLearnerMemoryServer({ data: { accountEmail, memoryId: 'x' } }),
    ).rejects.toThrow()
    expect(mocks.service.removeLearnerMemory).not.toHaveBeenCalled()
  })

  it('reports a missing memory as a result instead of losing the status code', async () => {
    mocks.service.getLearnerMemory.mockRejectedValue(new RestError('não existe', 404))

    await expect(
      getLearnerMemoryServer({ data: { accountEmail, memoryId } }),
    ).resolves.toEqual({ kind: 'not-found' })
  })

  it('rethrows other read failures', async () => {
    mocks.service.getLearnerMemory.mockRejectedValue(new RestError('falha', 500))

    await expect(
      getLearnerMemoryServer({ data: { accountEmail, memoryId } }),
    ).rejects.toThrow('falha')
  })

  it.each([
    [409, { kind: 'conflict' }],
    [422, { kind: 'invalid' }],
    [404, { kind: 'not-found' }],
  ])('maps an edit rejected with %s to a result', async (statusCode, expected) => {
    mocks.service.editLearnerMemory.mockRejectedValue(
      new RestError('rejeitado', statusCode),
    )

    await expect(
      editLearnerMemoryServer({
        data: { accountEmail, memoryId, content: 'Texto.', expectedVersion: 1 },
      }),
    ).resolves.toEqual(expected)
  })

  it.each([
    ['a server failure', new RestError('falha', 500)],
    ['a non-REST failure', new Error('rede')],
  ])('rethrows an edit that failed with %s', async (_description, error) => {
    mocks.service.editLearnerMemory.mockRejectedValue(error)

    await expect(
      editLearnerMemoryServer({
        data: { accountEmail, memoryId, content: 'Texto.', expectedVersion: 1 },
      }),
    ).rejects.toBe(error)
  })

  it('rethrows a failed deletion so the page can show it inline', async () => {
    mocks.service.removeLearnerMemory.mockRejectedValue(new RestError('falha', 503))

    await expect(
      removeLearnerMemoryServer({ data: { accountEmail, memoryId } }),
    ).rejects.toThrow('falha')
  })

  it('maps memory items of the session detail and defaults them to an empty list', async () => {
    const { IntelligenceService: createIntelligenceService } = await vi.importActual<
      typeof import('@/rest/services/intelligence-service')
    >('@/rest/services/intelligence-service')
    const sessionDetail = {
      session: {
        id: memoryId,
        title: 'Dúvida',
        created_at: '2026-10-14T10:00:00Z',
        updated_at: '2026-10-14T10:01:00Z',
        last_activity_at: '2026-10-14T10:01:00Z',
      },
      messages: { items: [], next_cursor: null },
      pending_learner_message_id: null,
      response: null,
      memory_items: [
        {
          id: '01J7T8AC91Z5K8M4JQ8C2D6F0C',
          source_message_id: '01J7T8AC91Z5K8M4JQ8C2D6F0D',
          kind: 'updated',
          category: 'explanation_preference',
          memory_id: memoryId,
          content: 'exemplos em Python.',
          previous_content: 'exemplos em JavaScript.',
          created_at: '2026-10-14T10:01:00Z',
        },
      ],
    }
    const get = vi
      .fn()
      .mockResolvedValueOnce(new RestResponse({ body: sessionDetail, statusCode: 200 }))
      .mockResolvedValueOnce(
        new RestResponse({
          body: { ...sessionDetail, memory_items: undefined },
          statusCode: 200,
        }),
      )
    mocks.axiosRestClient.mockReturnValue({ get } as unknown as RestClient)
    mocks.intelligenceService.mockImplementation((client: RestClient) =>
      createIntelligenceService(client),
    )

    const withItems = await getMentorSessionServer({
      data: { accountEmail, sessionId: memoryId },
    })
    const withoutItems = await getMentorSessionServer({
      data: { accountEmail, sessionId: memoryId },
    })

    expect(withItems.memoryItems).toEqual([
      {
        id: '01J7T8AC91Z5K8M4JQ8C2D6F0C',
        sourceMessageId: '01J7T8AC91Z5K8M4JQ8C2D6F0D',
        kind: 'updated',
        category: 'explanation_preference',
        memoryId,
        content: 'exemplos em Python.',
        previousContent: 'exemplos em JavaScript.',
        createdAt: '2026-10-14T10:01:00Z',
      },
    ])
    expect(withoutItems.memoryItems).toEqual([])
  })
})
