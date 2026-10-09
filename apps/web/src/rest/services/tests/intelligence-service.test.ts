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
