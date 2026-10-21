import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { RestClient } from '@/core/shared/interfaces/rest-client'
import { IntelligenceService } from '../intelligence-service'

const restClientMock = {
  delete: vi.fn(),
  get: vi.fn(),
  getFile: vi.fn(),
  patch: vi.fn(),
  post: vi.fn(),
  postFormData: vi.fn(),
  put: vi.fn(),
}

const restClient = restClientMock as unknown as RestClient
const SESSION_ID = '01J7T8AC91Z5K8M4JQ8C2D6F0B'
const CREATED_AT = '2026-10-08T10:00:00.000Z'

const sessionDto = {
  id: SESSION_ID,
  title: 'Matemática',
  created_at: CREATED_AT,
  updated_at: CREATED_AT,
  last_activity_at: CREATED_AT,
}

const learnerMessageDto = {
  id: '01J7T8AC91Z5K8M4JQ8C2D6F0C',
  session_id: SESSION_ID,
  role: 'learner',
  content: 'Quero estudar frações.',
  created_at: CREATED_AT,
  in_reply_to_message_id: null,
}

const detailDto = {
  session: sessionDto,
  messages: { items: [learnerMessageDto], next_cursor: 'older-page' },
  pending_learner_message_id: learnerMessageDto.id,
}

const success = (body: unknown) => ({
  isFailure: false,
  body,
  throwError: vi.fn(),
})
const failure = (error: Error) => ({
  isFailure: true,
  body: undefined,
  throwError: () => {
    throw error
  },
})

describe('IntelligenceService mentor session transport', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('maps all mentor operations to their HTTP contracts and domain values', async () => {
    restClientMock.get
      .mockResolvedValueOnce(success({ items: [sessionDto], next_cursor: 'next' }))
      .mockResolvedValueOnce(success(detailDto))
    restClientMock.post.mockResolvedValueOnce(success(detailDto))
    restClientMock.patch.mockResolvedValueOnce(success(sessionDto))
    restClientMock.delete.mockResolvedValueOnce(success(undefined))

    const service = IntelligenceService(restClient)
    const list = await service.listMentorSessions('token-123', {
      search: 'mate',
      cursor: 'list-cursor',
    })
    const created = await service.createMentorSession('token-123', {
      submissionKey: 'submission-key',
      firstMessage: '  Quero estudar frações.  ',
    })
    const detail = await service.getMentorSession(
      'token-123',
      '01J/session',
      'message-cursor',
    )
    const renamed = await service.renameMentorSession(
      'token-123',
      '01J/session',
      'Novo título',
    )
    await service.removeMentorSession('token-123', '01J/session')

    expect(list).toEqual({
      items: [
        {
          id: SESSION_ID,
          title: 'Matemática',
          createdAt: CREATED_AT,
          updatedAt: CREATED_AT,
          lastActivityAt: CREATED_AT,
        },
      ],
      nextCursor: 'next',
    })
    expect(created.messages.items[0]).toEqual({
      id: learnerMessageDto.id,
      sessionId: SESSION_ID,
      role: 'learner',
      content: 'Quero estudar frações.',
      createdAt: CREATED_AT,
      inReplyToMessageId: null,
      attachments: [],
    })
    expect(detail.pendingLearnerMessageId).toBe(learnerMessageDto.id)
    expect(detail.messages.nextCursor).toBe('older-page')
    expect(renamed.title).toBe('Matemática')

    const auth = {
      headers: {
        Authorization: 'Bearer token-123',
        'Cache-Control': 'no-store',
      },
    }
    expect(restClientMock.get).toHaveBeenNthCalledWith(
      1,
      '/intelligence/mentor-sessions',
      {
        ...auth,
        params: { search: 'mate', cursor: 'list-cursor' },
      },
    )
    expect(restClientMock.post).toHaveBeenCalledWith(
      '/intelligence/mentor-sessions',
      { submission_key: 'submission-key', first_message: '  Quero estudar frações.  ' },
      auth,
    )
    expect(restClientMock.get).toHaveBeenNthCalledWith(
      2,
      '/intelligence/mentor-sessions/01J%2Fsession',
      { ...auth, params: { cursor: 'message-cursor' } },
    )
    expect(restClientMock.patch).toHaveBeenCalledWith(
      '/intelligence/mentor-sessions/01J%2Fsession',
      { title: 'Novo título' },
      auth,
    )
    expect(restClientMock.delete).toHaveBeenCalledWith(
      '/intelligence/mentor-sessions/01J%2Fsession',
      undefined,
      auth,
    )
  })

  it('propagates failed REST responses from every mentor operation', async () => {
    const error = new Error('request failed')
    restClientMock.get.mockResolvedValue(failure(error))
    restClientMock.post.mockResolvedValue(failure(error))
    restClientMock.patch.mockResolvedValue(failure(error))
    restClientMock.delete.mockResolvedValue(failure(error))
    const service = IntelligenceService(restClient)

    await expect(service.listMentorSessions('token', {})).rejects.toBe(error)
    await expect(
      service.createMentorSession('token', {
        submissionKey: 'submission-key',
        firstMessage: 'Pergunta.',
      }),
    ).rejects.toBe(error)
    await expect(service.getMentorSession('token', SESSION_ID)).rejects.toBe(error)
    await expect(service.renameMentorSession('token', SESSION_ID, 'Título')).rejects.toBe(
      error,
    )
    await expect(service.removeMentorSession('token', SESSION_ID)).rejects.toBe(error)
  })
})

describe('IntelligenceService learner memories', () => {
  const MEMORY_ID = '01J7T8AC91Z5K8M4JQ8C2D6F0D'
  const auth = {
    headers: { Authorization: 'Bearer token-123', 'Cache-Control': 'no-store' },
  }
  const memoryDto = {
    id: MEMORY_ID,
    category: 'recurring_difficulty' as const,
    content: 'Confundo exibir e retornar valores.',
    version: 2,
    created_at: CREATED_AT,
    updated_at: '2026-10-09T10:00:00.000Z',
    origins: [
      {
        session_id: SESSION_ID,
        message_id: learnerMessageDto.id,
        conversation_title: 'Dúvida no laço for',
        is_available: true,
        declared_at: CREATED_AT,
      },
      {
        session_id: '01J7T8AC91Z5K8M4JQ8C2D6F0E',
        message_id: null,
        conversation_title: null,
        is_available: false,
        declared_at: CREATED_AT,
      },
    ],
    concepts: [{ key: 'retorno de valor', label: 'Retorno de valores' }],
  }
  const memory = {
    id: MEMORY_ID,
    category: 'recurring_difficulty',
    content: 'Confundo exibir e retornar valores.',
    version: 2,
    createdAt: CREATED_AT,
    updatedAt: '2026-10-09T10:00:00.000Z',
    origins: [
      {
        sessionId: SESSION_ID,
        messageId: learnerMessageDto.id,
        conversationTitle: 'Dúvida no laço for',
        isAvailable: true,
        declaredAt: CREATED_AT,
      },
      {
        sessionId: '01J7T8AC91Z5K8M4JQ8C2D6F0E',
        messageId: null,
        conversationTitle: null,
        isAvailable: false,
        declaredAt: CREATED_AT,
      },
    ],
    concepts: [{ key: 'retorno de valor', label: 'Retorno de valores' }],
  }

  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('lists the memories with their filters and maps origins and concepts', async () => {
    restClientMock.get.mockResolvedValue(success({ items: [memoryDto] }))

    const memories = await IntelligenceService(restClient).listLearnerMemories(
      'token-123',
      { q: 'valores', category: 'recurring_difficulty' },
    )

    expect(restClientMock.get).toHaveBeenCalledWith('/intelligence/learner-memories', {
      ...auth,
      params: { q: 'valores', category: 'recurring_difficulty' },
    })
    expect(memories).toEqual([memory])
  })

  it('lists without filters', async () => {
    restClientMock.get.mockResolvedValue(success({ items: [] }))

    const memories = await IntelligenceService(restClient).listLearnerMemories(
      'token-123',
      {},
    )

    expect(restClientMock.get).toHaveBeenCalledWith('/intelligence/learner-memories', {
      ...auth,
      params: { q: undefined, category: undefined },
    })
    expect(memories).toEqual([])
  })

  it('reads one memory by id', async () => {
    restClientMock.get.mockResolvedValue(success(memoryDto))

    const result = await IntelligenceService(restClient).getLearnerMemory(
      'token-123',
      MEMORY_ID,
    )

    expect(restClientMock.get).toHaveBeenCalledWith(
      `/intelligence/learner-memories/${MEMORY_ID}`,
      auth,
    )
    expect(result).toEqual(memory)
  })

  it('edits a memory with its expected version', async () => {
    restClientMock.patch.mockResolvedValue(success(memoryDto))

    const result = await IntelligenceService(restClient).editLearnerMemory(
      'token-123',
      MEMORY_ID,
      { content: 'Novo texto.', expectedVersion: 1 },
    )

    expect(restClientMock.patch).toHaveBeenCalledWith(
      `/intelligence/learner-memories/${MEMORY_ID}`,
      { content: 'Novo texto.', expected_version: 1 },
      auth,
    )
    expect(result.version).toBe(2)
  })

  it('deletes a memory', async () => {
    restClientMock.delete.mockResolvedValue(success(undefined))

    await IntelligenceService(restClient).removeLearnerMemory('token-123', MEMORY_ID)

    expect(restClientMock.delete).toHaveBeenCalledWith(
      `/intelligence/learner-memories/${MEMORY_ID}`,
      undefined,
      auth,
    )
  })

  it('propagates failed REST responses from every memory operation', async () => {
    const error = new Error('request failed')
    restClientMock.get.mockResolvedValue(failure(error))
    restClientMock.patch.mockResolvedValue(failure(error))
    restClientMock.delete.mockResolvedValue(failure(error))
    const service = IntelligenceService(restClient)

    await expect(service.listLearnerMemories('token', {})).rejects.toBe(error)
    await expect(service.getLearnerMemory('token', MEMORY_ID)).rejects.toBe(error)
    await expect(
      service.editLearnerMemory('token', MEMORY_ID, { content: 'a', expectedVersion: 1 }),
    ).rejects.toBe(error)
    await expect(service.removeLearnerMemory('token', MEMORY_ID)).rejects.toBe(error)
  })

  it('maps the memory items of a session detail and defaults them to an empty list', async () => {
    const item = {
      id: '01J7T8AC91Z5K8M4JQ8C2D6F0F',
      source_message_id: learnerMessageDto.id,
      kind: 'created' as const,
      category: 'explanation_preference' as const,
      memory_id: MEMORY_ID,
      content: 'exemplos curtos.',
      previous_content: null,
      created_at: CREATED_AT,
    }
    restClientMock.get
      .mockResolvedValueOnce(success({ ...detailDto, memory_items: [item] }))
      .mockResolvedValueOnce(success(detailDto))
    const service = IntelligenceService(restClient)

    const withItems = await service.getMentorSession('token-123', SESSION_ID)
    const withoutItems = await service.getMentorSession('token-123', SESSION_ID)

    expect(withItems.memoryItems).toEqual([
      {
        id: item.id,
        sourceMessageId: learnerMessageDto.id,
        kind: 'created',
        category: 'explanation_preference',
        memoryId: MEMORY_ID,
        content: 'exemplos curtos.',
        previousContent: null,
        createdAt: CREATED_AT,
      },
    ])
    expect(withoutItems.memoryItems).toEqual([])
  })
})
