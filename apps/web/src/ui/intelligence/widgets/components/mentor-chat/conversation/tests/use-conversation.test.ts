import { cleanup, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { MentorResponseSnapshot } from '@/core/intelligence/mentor-response'
import type {
  MentorSessionSummaryState,
  MentorSummaryMarker,
} from '@/core/intelligence/mentor-session-summary'
import type { MentorMessage } from '@/rest/services/intelligence-service'
import type { MentorContextValue } from '@/ui/intelligence/contexts/mentor-context/types'
import { useMentorContext } from '@/ui/intelligence/hooks/use-mentor-context'

import { useConversation } from '../use-conversation'

vi.mock('@/ui/intelligence/hooks/use-mentor-context', () => ({
  useMentorContext: vi.fn(),
}))

const useMentorContextMock = vi.mocked(useMentorContext)
const NO_SUMMARY: MentorSessionSummaryState = {
  current: null,
  failureAfterMessageId: null,
}
const MARKER: MentorSummaryMarker = {
  version: 2,
  boundaryMessageId: 'm2',
  coveredMessageCount: 21,
  completedAt: '2026-10-18T14:00:00Z',
}

function buildMessage(id: string): MentorMessage {
  return {
    id,
    sessionId: 'session',
    role: 'learner',
    content: `Mensagem ${id}`,
    inReplyToMessageId: null,
    createdAt: '',
    attachments: [],
  }
}

function mockSummaryContext(input: {
  messageIds: string[]
  summary: MentorSessionSummaryState
  isSummarizingContext?: boolean
}) {
  const messages = input.messageIds.map(buildMessage)
  useMentorContextMock.mockReturnValue({
    selectedSessionId: 'session',
    sessionDetail: {
      session: {
        id: 'session',
        title: 'Conversa',
        createdAt: '',
        updatedAt: '',
        lastActivityAt: '',
      },
      messages: { items: messages, nextCursor: null },
      pendingLearnerMessageId: null,
      response: null,
      summary: input.summary,
    },
    response: null,
    summary: input.summary,
    isSummarizingContext: input.isSummarizingContext ?? false,
    isReadingMessages: false,
    loadOlderMessages: vi.fn(),
  } as unknown as MentorContextValue)
  return messages
}

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
      summary: NO_SUMMARY,
      isSummarizingContext: false,
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
      summary: NO_SUMMARY,
      isSummarizingContext: false,
      isReadingMessages: false,
      loadOlderMessages: vi.fn(),
    } as unknown as MentorContextValue
    useMentorContextMock.mockReturnValue(context)

    const { result } = renderHook(() => useConversation())

    expect(result.current.visibleMessages).toEqual([reply])
  })
  it('places the summary marker right after the loaded boundary message', () => {
    const messages = mockSummaryContext({
      messageIds: ['m1', 'm2', 'm3'],
      summary: { current: MARKER, failureAfterMessageId: null },
    })

    const { result } = renderHook(() => useConversation())

    expect(result.current.conversationItems).toEqual([
      { kind: 'message', message: messages[0] },
      { kind: 'message', message: messages[1] },
      { kind: 'summary-marker', marker: MARKER },
      { kind: 'message', message: messages[2] },
    ])
  })

  it('places the summary marker at the top when the boundary is in an unloaded older page', () => {
    const messages = mockSummaryContext({
      messageIds: ['m3', 'm4'],
      summary: { current: MARKER, failureAfterMessageId: null },
    })

    const { result } = renderHook(() => useConversation())

    expect(result.current.conversationItems).toEqual([
      { kind: 'summary-marker', marker: MARKER },
      { kind: 'message', message: messages[0] },
      { kind: 'message', message: messages[1] },
    ])
  })

  it('places the failure notice after its message and hides it while summarizing', () => {
    const summary: MentorSessionSummaryState = {
      current: null,
      failureAfterMessageId: 'm2',
    }
    const messages = mockSummaryContext({ messageIds: ['m1', 'm2', 'm3'], summary })

    const { result, rerender } = renderHook(() => useConversation())

    expect(result.current.conversationItems).toEqual([
      { kind: 'message', message: messages[0] },
      { kind: 'message', message: messages[1] },
      { kind: 'summary-failure', messageId: 'm2' },
      { kind: 'message', message: messages[2] },
    ])

    mockSummaryContext({
      messageIds: ['m1', 'm2', 'm3'],
      summary,
      isSummarizingContext: true,
    })
    rerender()

    expect(
      result.current.conversationItems.filter((item) => item.kind === 'summary-failure'),
    ).toEqual([])
    expect(result.current.isSummarizingContext).toBe(true)
  })

  it('lists only messages when the conversation has no summary state', () => {
    const messages = mockSummaryContext({ messageIds: ['m1'], summary: NO_SUMMARY })

    const { result } = renderHook(() => useConversation())

    expect(result.current.conversationItems).toEqual([
      { kind: 'message', message: messages[0] },
    ])
  })
})
