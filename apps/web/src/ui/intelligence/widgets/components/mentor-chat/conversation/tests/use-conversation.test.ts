import { cleanup, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { MentorResponseSnapshot } from '@/core/intelligence/mentor-response'
import type { MentorMessage } from '@/rest/services/intelligence-service'
import type { MentorContextValue } from '@/ui/intelligence/contexts/mentor-context/types'
import { useMentorContext } from '@/ui/intelligence/hooks/use-mentor-context'

import { useConversation } from '../use-conversation'

vi.mock('@/ui/intelligence/hooks/use-mentor-context', () => ({
  useMentorContext: vi.fn(),
}))

const useMentorContextMock = vi.mocked(useMentorContext)

describe('useConversation', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('keeps the live response as the only presentation for its persisted reply', () => {
    const response: MentorResponseSnapshot = {
      attemptId: 'attempt',
      learnerMessageId: 'learner',
      status: 'completed',
      blocks: [
        {
          blockKey: 'block',
          ordinal: 0,
          intent: null,
          content: 'Resposta aprovada.',
          sources: [],
        },
      ],
      consultations: [],
      lastSequence: 2,
      failureCode: null,
    }
    const learnerMessage: MentorMessage = {
      id: 'learner',
      sessionId: 'session',
      role: 'learner',
      content: 'Pergunta atual',
      inReplyToMessageId: null,
      createdAt: '',
      attachments: [],
    }
    const currentReply: MentorMessage = {
      id: 'current-reply',
      sessionId: 'session',
      role: 'mentor',
      content: 'Resposta aprovada.',
      inReplyToMessageId: 'learner',
      createdAt: '',
      attachments: [],
    }
    const olderReply: MentorMessage = {
      id: 'older-reply',
      sessionId: 'session',
      role: 'mentor',
      content: 'Resposta anterior.',
      inReplyToMessageId: 'older-learner',
      createdAt: '',
      attachments: [],
    }
    const context = {
      selectedSessionId: 'session',
      sessionDetail: {
        session: {
          id: 'session',
          title: 'Conversa',
          createdAt: '',
          updatedAt: '',
          lastActivityAt: '',
        },
        messages: {
          items: [learnerMessage, currentReply, olderReply],
          nextCursor: null,
        },
        pendingLearnerMessageId: null,
        response,
      },
      response,
      isReadingMessages: false,
      loadOlderMessages: vi.fn(),
    } as unknown as MentorContextValue
    useMentorContextMock.mockReturnValue(context)

    const { result } = renderHook(() => useConversation())

    expect(result.current.visibleMessages).toEqual([learnerMessage, olderReply])
  })

  it('keeps persisted replies in the history when no response block is being presented', () => {
    const reply: MentorMessage = {
      id: 'reply',
      sessionId: 'session',
      role: 'mentor',
      content: 'Resposta anterior.',
      inReplyToMessageId: 'learner',
      createdAt: '',
      attachments: [],
    }
    const context = {
      selectedSessionId: 'session',
      sessionDetail: {
        session: {
          id: 'session',
          title: 'Conversa',
          createdAt: '',
          updatedAt: '',
          lastActivityAt: '',
        },
        messages: { items: [reply], nextCursor: null },
        pendingLearnerMessageId: null,
        response: null,
      },
      response: null,
      isReadingMessages: false,
      loadOlderMessages: vi.fn(),
    } as unknown as MentorContextValue
    useMentorContextMock.mockReturnValue(context)

    const { result } = renderHook(() => useConversation())

    expect(result.current.visibleMessages).toEqual([reply])
  })
})
