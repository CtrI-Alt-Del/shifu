import { act, cleanup, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { MentorResponseSnapshot } from '@/core/intelligence/mentor-response'
import type {
  MentorSessionSummaryState,
  MentorSummaryMarker,
} from '@/core/intelligence/mentor-session-summary'
import { LearnerMemoryFaker } from '@/core/intelligence/fakers/learner-memory-faker'
import type { MentorConversationMemoryItem } from '@/core/intelligence/learner-memory'
import type { MentorActionProposal } from '@/core/intelligence/mentor-action-proposal'
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
  afterMessageId: null,
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

  it('places the summary marker right after the learner message that triggered it', () => {
    const marker = { ...MARKER, afterMessageId: 'm4' }
    const messages = mockSummaryContext({
      messageIds: ['m1', 'm2', 'm3', 'm4', 'm5'],
      summary: { current: marker, failureAfterMessageId: null },
    })

    const { result } = renderHook(() => useConversation())

    expect(result.current.conversationItems).toEqual([
      { kind: 'message', message: messages[0] },
      { kind: 'message', message: messages[1] },
      { kind: 'message', message: messages[2] },
      { kind: 'message', message: messages[3] },
      { kind: 'summary-marker', marker },
      { kind: 'message', message: messages[4] },
    ])
  })

  it('places the marker at the trigger even when the boundary is in an unloaded older page', () => {
    const marker = { ...MARKER, boundaryMessageId: 'unloaded', afterMessageId: 'm3' }
    const messages = mockSummaryContext({
      messageIds: ['m3', 'm4'],
      summary: { current: marker, failureAfterMessageId: null },
    })

    const { result } = renderHook(() => useConversation())

    expect(result.current.conversationItems).toEqual([
      { kind: 'message', message: messages[0] },
      { kind: 'summary-marker', marker },
      { kind: 'message', message: messages[1] },
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

describe('useConversation memory markers', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  function buildTurnMessage(
    id: string,
    role: MentorMessage['role'],
    inReplyToMessageId: string | null = null,
  ): MentorMessage {
    return {
      id,
      sessionId: 'session',
      role,
      content: `Mensagem ${id}`,
      inReplyToMessageId,
      createdAt: '',
      attachments: [],
    }
  }

  function buildItem(
    id: string,
    sourceMessageId: string,
    overrides: Partial<MentorConversationMemoryItem> = {},
  ) {
    return LearnerMemoryFaker.fakeConversationItem({ id, sourceMessageId, ...overrides })
  }

  function mockTurns(input: {
    messages: MentorMessage[]
    memoryItems: MentorConversationMemoryItem[]
    response?: MentorResponseSnapshot | null
    summary?: MentorSessionSummaryState
  }) {
    const summary = input.summary ?? NO_SUMMARY
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
        messages: { items: input.messages, nextCursor: null },
        pendingLearnerMessageId: null,
        response: input.response ?? null,
        summary,
        memoryItems: input.memoryItems,
      },
      response: input.response ?? null,
      summary,
      isSummarizingContext: false,
      isReadingMessages: false,
      loadOlderMessages: vi.fn(),
    } as unknown as MentorContextValue)
  }

  function liveResponse(
    learnerMessageId: string,
    withBlock: boolean,
  ): MentorResponseSnapshot {
    return {
      attemptId: 'attempt',
      learnerMessageId,
      status: withBlock ? 'completed' : 'failed',
      blocks: withBlock
        ? [
            {
              blockKey: 'b1',
              ordinal: 0,
              intent: null,
              content: 'Resposta.',
              sources: [],
            },
          ]
        : [],
      consultations: [],
      lastSequence: 3,
      failureCode: null,
    }
  }

  function describeItems(items: ReturnType<typeof useConversation>['conversationItems']) {
    return items.map((item) =>
      item.kind === 'message'
        ? item.message.id
        : item.kind === 'memory-change'
          ? `memory:${item.item.id}`
          : item.kind,
    )
  }

  it('places a marker right after the answer of the turn that produced it', () => {
    const marker = buildItem('c1', 'q1')
    mockTurns({
      messages: [
        buildTurnMessage('q1', 'learner'),
        buildTurnMessage('a1', 'mentor', 'q1'),
        buildTurnMessage('q2', 'learner'),
      ],
      memoryItems: [marker],
    })

    const { result } = renderHook(() => useConversation())

    expect(describeItems(result.current.conversationItems)).toEqual([
      'q1',
      'a1',
      'memory:c1',
      'q2',
    ])
    expect(result.current.trailingMemoryItems).toEqual([])
  })

  it('places a marker right after the learner message when no answer exists', () => {
    mockTurns({
      messages: [buildTurnMessage('q1', 'learner'), buildTurnMessage('q2', 'learner')],
      memoryItems: [buildItem('c1', 'q1')],
    })

    const { result } = renderHook(() => useConversation())

    expect(describeItems(result.current.conversationItems)).toEqual([
      'q1',
      'memory:c1',
      'q2',
    ])
  })

  it('keeps created, updated and deleted items in creation order after the answer', () => {
    const created = buildItem('c1', 'q1', { kind: 'created' })
    const updated = buildItem('c2', 'q1', {
      kind: 'updated',
      previousContent: 'Antes',
    })
    const deleted = buildItem('c3', 'q1', {
      memoryId: null,
      content: null,
      previousContent: null,
    })
    mockTurns({
      messages: [
        buildTurnMessage('q1', 'learner'),
        buildTurnMessage('a1', 'mentor', 'q1'),
      ],
      memoryItems: [created, updated, deleted],
    })

    const { result } = renderHook(() => useConversation())

    expect(describeItems(result.current.conversationItems)).toEqual([
      'q1',
      'a1',
      'memory:c1',
      'memory:c2',
      'memory:c3',
    ])
  })

  it('anchors the marker after the last answer when a turn has several replies', () => {
    mockTurns({
      messages: [
        buildTurnMessage('q1', 'learner'),
        buildTurnMessage('a1', 'mentor', 'q1'),
        buildTurnMessage('a2', 'mentor', 'q1'),
      ],
      memoryItems: [buildItem('c1', 'q1')],
    })

    const { result } = renderHook(() => useConversation())

    expect(describeItems(result.current.conversationItems)).toEqual([
      'q1',
      'a1',
      'a2',
      'memory:c1',
    ])
  })

  it('does not show items whose source message is not loaded', () => {
    mockTurns({
      messages: [buildTurnMessage('q2', 'learner')],
      memoryItems: [buildItem('c1', 'q1-in-an-older-page')],
    })

    const { result } = renderHook(() => useConversation())

    expect(describeItems(result.current.conversationItems)).toEqual(['q2'])
    expect(result.current.trailingMemoryItems).toEqual([])
  })

  it('moves the markers of a live answered turn to the trailing slot', () => {
    const live = buildItem('c2', 'q2')
    const older = buildItem('c1', 'q1')
    mockTurns({
      messages: [
        buildTurnMessage('q1', 'learner'),
        buildTurnMessage('a1', 'mentor', 'q1'),
        buildTurnMessage('q2', 'learner'),
        buildTurnMessage('a2', 'mentor', 'q2'),
      ],
      memoryItems: [older, live],
      response: liveResponse('q2', true),
    })

    const { result } = renderHook(() => useConversation())

    expect(describeItems(result.current.conversationItems)).toEqual([
      'q1',
      'a1',
      'memory:c1',
      'q2',
    ])
    expect(result.current.trailingMemoryItems).toEqual([live])
  })

  it('keeps the markers after the learner message when the response has no blocks', () => {
    const marker = buildItem('c1', 'q1')
    mockTurns({
      messages: [buildTurnMessage('q1', 'learner')],
      memoryItems: [marker],
      response: liveResponse('q1', false),
    })

    const { result } = renderHook(() => useConversation())

    expect(describeItems(result.current.conversationItems)).toEqual(['q1', 'memory:c1'])
    expect(result.current.trailingMemoryItems).toEqual([])
  })

  it('does not use the trailing slot when the live turn message is not loaded', () => {
    mockTurns({
      messages: [buildTurnMessage('q0', 'learner')],
      memoryItems: [buildItem('c1', 'q9')],
      response: liveResponse('q9', true),
    })

    const { result } = renderHook(() => useConversation())

    expect(result.current.trailingMemoryItems).toEqual([])
  })

  it('places a marker after the summary marker when there is no answer', () => {
    mockTurns({
      messages: [buildTurnMessage('q1', 'learner')],
      memoryItems: [buildItem('c1', 'q1')],
      summary: {
        current: { ...MARKER, boundaryMessageId: 'q1', afterMessageId: 'q1' },
        failureAfterMessageId: null,
      },
    })

    const { result } = renderHook(() => useConversation())

    expect(describeItems(result.current.conversationItems)).toEqual([
      'q1',
      'summary-marker',
      'memory:c1',
    ])
  })

  it('tolerates a detail without memory items', () => {
    mockTurns({
      messages: [buildTurnMessage('q1', 'learner')],
      memoryItems: undefined as unknown as MentorConversationMemoryItem[],
    })

    const { result } = renderHook(() => useConversation())

    expect(describeItems(result.current.conversationItems)).toEqual(['q1'])
  })
})

describe('useConversation action items', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  function buildTurnMessage(
    id: string,
    role: MentorMessage['role'],
    inReplyToMessageId: string | null = null,
  ): MentorMessage {
    return {
      id,
      sessionId: 'session',
      role,
      content: `Mensagem ${id}`,
      inReplyToMessageId,
      createdAt: '',
      attachments: [],
    }
  }

  function buildProposal(
    id: string,
    sourceMessageId: string,
    overrides: Partial<MentorActionProposal> = {},
  ): MentorActionProposal {
    return {
      id,
      sourceMessageId,
      kind: 'add_skill',
      skillId: 'skill',
      skillName: 'Funções em Python',
      goalId: 'goal',
      goalTitle: 'Aprender a programar',
      skillExperienceId: null,
      candidateGoals: [],
      justification: null,
      status: 'pending',
      outcome: null,
      rejectionReason: null,
      resolvedGoalId: null,
      resolvedSkillExperienceId: null,
      createdAt: '',
      ...overrides,
    }
  }

  function mockTurns(input: {
    messages: MentorMessage[]
    actionItems?: MentorActionProposal[]
    memoryItems?: MentorConversationMemoryItem[]
    response?: MentorResponseSnapshot | null
  }) {
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
        messages: { items: input.messages, nextCursor: null },
        pendingLearnerMessageId: null,
        response: input.response ?? null,
        summary: NO_SUMMARY,
        memoryItems: input.memoryItems ?? [],
        actionItems: input.actionItems,
      },
      response: input.response ?? null,
      summary: NO_SUMMARY,
      isSummarizingContext: false,
      isReadingMessages: false,
      loadOlderMessages: vi.fn(),
    } as unknown as MentorContextValue)
  }

  function liveResponse(
    learnerMessageId: string,
    withBlock: boolean,
  ): MentorResponseSnapshot {
    return {
      attemptId: 'attempt',
      learnerMessageId,
      status: withBlock ? 'processing' : 'failed',
      blocks: withBlock
        ? [
            {
              blockKey: 'b1',
              ordinal: 0,
              intent: 'add_skill',
              content: 'Preparei uma proposta para você confirmar.',
              sources: [],
            },
          ]
        : [],
      consultations: [],
      lastSequence: 3,
      failureCode: null,
    }
  }

  function describeItems(items: ReturnType<typeof useConversation>['conversationItems']) {
    return items.map((item) =>
      item.kind === 'message'
        ? item.message.id
        : item.kind === 'action'
          ? `action:${item.proposal.id}`
          : item.kind === 'memory-change'
            ? `memory:${item.item.id}`
            : item.kind,
    )
  }

  it('places the card right after the answer of the turn that produced it', () => {
    mockTurns({
      messages: [
        buildTurnMessage('q1', 'learner'),
        buildTurnMessage('a1', 'mentor', 'q1'),
        buildTurnMessage('q2', 'learner'),
      ],
      actionItems: [buildProposal('p1', 'q1')],
    })

    const { result } = renderHook(() => useConversation())

    expect(describeItems(result.current.conversationItems)).toEqual([
      'q1',
      'a1',
      'action:p1',
      'q2',
    ])
    expect(result.current.trailingActionItems).toEqual([])
  })

  it('places the card right after the learner message when no answer is shown', () => {
    mockTurns({
      messages: [buildTurnMessage('q1', 'learner'), buildTurnMessage('q2', 'learner')],
      actionItems: [buildProposal('p1', 'q1')],
    })

    const { result } = renderHook(() => useConversation())

    expect(describeItems(result.current.conversationItems)).toEqual([
      'q1',
      'action:p1',
      'q2',
    ])
  })

  it('shows the card of the turn before the memory markers of the same turn', () => {
    mockTurns({
      messages: [
        buildTurnMessage('q1', 'learner'),
        buildTurnMessage('a1', 'mentor', 'q1'),
      ],
      actionItems: [buildProposal('p1', 'q1')],
      memoryItems: [
        LearnerMemoryFaker.fakeConversationItem({ id: 'm1', sourceMessageId: 'q1' }),
      ],
    })

    const { result } = renderHook(() => useConversation())

    expect(describeItems(result.current.conversationItems)).toEqual([
      'q1',
      'a1',
      'action:p1',
      'memory:m1',
    ])
  })

  it('anchors the card after the last answer when a turn has several replies', () => {
    mockTurns({
      messages: [
        buildTurnMessage('q1', 'learner'),
        buildTurnMessage('a1', 'mentor', 'q1'),
        buildTurnMessage('a2', 'mentor', 'q1'),
      ],
      actionItems: [buildProposal('p1', 'q1')],
    })

    const { result } = renderHook(() => useConversation())

    expect(describeItems(result.current.conversationItems)).toEqual([
      'q1',
      'a1',
      'a2',
      'action:p1',
    ])
  })

  it('moves the card of a live answered turn to the trailing slot', () => {
    const live = buildProposal('p2', 'q2')
    mockTurns({
      messages: [
        buildTurnMessage('q1', 'learner'),
        buildTurnMessage('a1', 'mentor', 'q1'),
        buildTurnMessage('q2', 'learner'),
      ],
      actionItems: [buildProposal('p1', 'q1'), live],
      response: liveResponse('q2', true),
    })

    const { result } = renderHook(() => useConversation())

    expect(describeItems(result.current.conversationItems)).toEqual([
      'q1',
      'a1',
      'action:p1',
      'q2',
    ])
    expect(result.current.trailingActionItems).toEqual([live])
  })

  it('keeps the card after the learner message when the response has no blocks', () => {
    mockTurns({
      messages: [buildTurnMessage('q1', 'learner')],
      actionItems: [buildProposal('p1', 'q1')],
      response: liveResponse('q1', false),
    })

    const { result } = renderHook(() => useConversation())

    expect(describeItems(result.current.conversationItems)).toEqual(['q1', 'action:p1'])
    expect(result.current.trailingActionItems).toEqual([])
  })

  it('does not show a card whose source message is not loaded', () => {
    mockTurns({
      messages: [buildTurnMessage('q1', 'learner')],
      actionItems: [buildProposal('p1', 'q-older')],
    })

    const { result } = renderHook(() => useConversation())

    expect(describeItems(result.current.conversationItems)).toEqual(['q1'])
    expect(result.current.trailingActionItems).toEqual([])
  })

  it('tolerates a detail without action items', () => {
    mockTurns({ messages: [buildTurnMessage('q1', 'learner')] })

    const { result } = renderHook(() => useConversation())

    expect(describeItems(result.current.conversationItems)).toEqual(['q1'])
    expect(result.current.trailingActionItems).toEqual([])
  })
})

describe('useConversation scrolling', () => {
  const loadOlderMessagesMock = vi.fn()

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  function buildScrollMessage(id: string, role: MentorMessage['role']): MentorMessage {
    return {
      id,
      sessionId: 'session',
      role,
      content: `Mensagem ${id}`,
      inReplyToMessageId: role === 'mentor' ? 'm1' : null,
      createdAt: '',
      attachments: [],
    }
  }

  function mockScrollContext(
    messages: MentorMessage[],
    extra: Record<string, unknown> = {},
    nextCursor: string | null = null,
  ) {
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
        messages: { items: messages, nextCursor },
        pendingLearnerMessageId: null,
        response: null,
        summary: NO_SUMMARY,
        memoryItems: [],
      },
      response: null,
      summary: NO_SUMMARY,
      isSummarizingContext: false,
      isReadingMessages: false,
      loadOlderMessages: loadOlderMessagesMock,
      ...extra,
    } as unknown as MentorContextValue)
  }

  function attachScrollElement(
    result: { current: ReturnType<typeof useConversation> },
    geometry: { scrollTop: number; scrollHeight: number; clientHeight: number },
  ) {
    const element = { ...geometry }
    result.current.scrollRef.current = element as unknown as HTMLDivElement
    return element
  }

  it('scrolls to the bottom when the conversation is first shown', () => {
    mockScrollContext([])
    const { result, rerender } = renderHook(() => useConversation())
    const element = attachScrollElement(result, {
      scrollTop: 0,
      scrollHeight: 1000,
      clientHeight: 400,
    })

    mockScrollContext([buildScrollMessage('m1', 'learner')], {
      selectedSessionId: 'other',
      sessionDetail: {
        session: { id: 'other' },
        messages: { items: [buildScrollMessage('m1', 'learner')], nextCursor: null },
        memoryItems: [],
      },
    })
    rerender()

    expect(element.scrollTop).toBe(1000)
  })

  it('follows a new message while the reader is at the bottom', () => {
    mockScrollContext([buildScrollMessage('m1', 'learner')])
    const { result, rerender } = renderHook(() => useConversation())
    const element = attachScrollElement(result, {
      scrollTop: 600,
      scrollHeight: 1000,
      clientHeight: 400,
    })
    act(() => result.current.handleScroll())

    mockScrollContext([
      buildScrollMessage('m1', 'learner'),
      buildScrollMessage('m2', 'mentor'),
    ])
    rerender()

    expect(element.scrollTop).toBe(1000)
  })

  it('keeps the reading position when scrolled away and the newest message is the mentor reply', () => {
    mockScrollContext([buildScrollMessage('m1', 'learner')])
    const { result, rerender } = renderHook(() => useConversation())
    const element = attachScrollElement(result, {
      scrollTop: 100,
      scrollHeight: 1000,
      clientHeight: 400,
    })
    act(() => result.current.handleScroll())

    mockScrollContext([
      buildScrollMessage('m1', 'learner'),
      buildScrollMessage('m2', 'mentor'),
    ])
    rerender()

    expect(element.scrollTop).toBe(100)
  })

  it('jumps to a learner message that was just sent even when scrolled away', () => {
    mockScrollContext([buildScrollMessage('m1', 'learner')])
    const { result, rerender } = renderHook(() => useConversation())
    const element = attachScrollElement(result, {
      scrollTop: 100,
      scrollHeight: 1000,
      clientHeight: 400,
    })
    act(() => result.current.handleScroll())

    mockScrollContext([
      buildScrollMessage('m1', 'learner'),
      buildScrollMessage('m2', 'learner'),
    ])
    rerender()

    expect(element.scrollTop).toBe(1000)
  })

  it('loads older messages near the top and preserves the reading position afterwards', () => {
    mockScrollContext([buildScrollMessage('m2', 'learner')], {}, 'older-cursor')
    const { result, rerender } = renderHook(() => useConversation())
    const element = attachScrollElement(result, {
      scrollTop: 10,
      scrollHeight: 1000,
      clientHeight: 400,
    })

    act(() => result.current.handleScroll())
    expect(loadOlderMessagesMock).toHaveBeenCalledOnce()

    element.scrollHeight = 1600
    mockScrollContext(
      [buildScrollMessage('m1', 'learner'), buildScrollMessage('m2', 'learner')],
      {},
      'older-cursor',
    )
    rerender()

    expect(element.scrollTop).toBe(610)
  })

  it.each([
    ['the reader is away from the top', { scrollTop: 200 }, {}],
    ['there is no older page', { scrollTop: 0 }, { noCursor: true }],
    ['a read is already running', { scrollTop: 0 }, { isReadingMessages: true }],
  ])('does not load older messages when %s', (_description, geometry, options) => {
    if ('noCursor' in options) mockScrollContext([buildScrollMessage('m1', 'learner')])
    else
      mockScrollContext(
        [buildScrollMessage('m1', 'learner')],
        { isReadingMessages: 'isReadingMessages' in options },
        'older-cursor',
      )
    const { result } = renderHook(() => useConversation())
    attachScrollElement(result, {
      ...geometry,
      scrollHeight: 1000,
      clientHeight: 400,
    })

    act(() => result.current.handleScroll())

    expect(loadOlderMessagesMock).not.toHaveBeenCalled()
  })

  it('ignores a scroll event before the list is attached', () => {
    mockScrollContext([buildScrollMessage('m1', 'learner')])
    const { result } = renderHook(() => useConversation())

    expect(() => act(() => result.current.handleScroll())).not.toThrow()
    expect(loadOlderMessagesMock).not.toHaveBeenCalled()
  })

  it('returns a new conversation to the top with scrollTo or a scrollTop fallback', () => {
    mockScrollContext([], { selectedSessionId: null, sessionDetail: null })
    const { result, rerender } = renderHook(() => useConversation())
    const scrollTo = vi.fn()
    result.current.scrollRef.current = {
      scrollTo,
      scrollTop: 50,
    } as unknown as HTMLDivElement
    mockScrollContext([], { selectedSessionId: 'x', sessionDetail: null })
    rerender()
    mockScrollContext([], { selectedSessionId: null, sessionDetail: null })
    rerender()
    expect(scrollTo).toHaveBeenCalledWith({ top: 0 })

    const legacy = { scrollTop: 50 } as unknown as HTMLDivElement
    result.current.scrollRef.current = legacy
    mockScrollContext([], { selectedSessionId: 'y', sessionDetail: null })
    rerender()
    mockScrollContext([], { selectedSessionId: null, sessionDetail: null })
    rerender()
    expect(legacy.scrollTop).toBe(0)
  })
})
