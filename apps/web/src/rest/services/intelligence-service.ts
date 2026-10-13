import { AppError } from '@/core/errors/app-error'
import type { RestStreamClient } from '@/core/shared/interfaces/rest-stream-client'
import type {
  MentorContextHint,
  MentorResponseSnapshot,
  MentorResponseStatus,
  SubmitMentorMessageInput,
} from '@/core/intelligence/mentor-response'
import type { RestClient } from '@/core/shared/interfaces/rest-client'

export type MentorSession = {
  id: string
  title: string
  createdAt: string
  updatedAt: string
  lastActivityAt: string
}

export type MentorMessage = {
  id: string
  sessionId: string
  role: 'learner' | 'mentor'
  content: string
  createdAt: string
  inReplyToMessageId: string | null
}

export type MentorSessionsPage = {
  items: MentorSession[]
  nextCursor: string | null
}

export type MentorMessagesPage = {
  items: MentorMessage[]
  nextCursor: string | null
}

export type MentorSessionDetail = {
  session: MentorSession
  messages: MentorMessagesPage
  pendingLearnerMessageId: string | null
  response?: MentorResponseSnapshot | null
}

export type CreateMentorSessionInput = {
  submissionKey: string
  firstMessage: string
  contextHint?: MentorContextHint | null
}

type MentorSessionDto = {
  id: string
  title: string
  created_at: string
  updated_at: string
  last_activity_at: string
}

type MentorMessageDto = {
  id: string
  session_id: string
  role: 'learner' | 'mentor'
  content: string
  created_at: string
  in_reply_to_message_id: string | null
}

type MentorSessionsPageDto = {
  items: MentorSessionDto[]
  next_cursor: string | null
}

type MentorMessagesPageDto = {
  items: MentorMessageDto[]
  next_cursor: string | null
}

type MentorSessionDetailDto = {
  session: MentorSessionDto
  messages: MentorMessagesPageDto
  pending_learner_message_id: string | null
  response?: MentorResponseSnapshotDto | null
}

type MentorResponseSnapshotDto = {
  progress?: MentorResponseSnapshot['progress']
  attempt_id: string
  learner_message_id: string
  status: MentorResponseStatus
  blocks: { block_key: string; ordinal: number; intent: string | null; content: string }[]
  consultations: string[]
  last_sequence: number
  failure_code: string | null
}
export type IntelligenceService = ReturnType<typeof IntelligenceService>

export const IntelligenceService = (
  restClient: RestClient,
  streamClient?: RestStreamClient,
) => {
  const auth = (accessToken: string) => ({
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Cache-Control': 'no-store',
    },
  })

  function mapSession(session: MentorSessionDto): MentorSession {
    return {
      id: session.id,
      title: session.title,
      createdAt: session.created_at,
      updatedAt: session.updated_at,
      lastActivityAt: session.last_activity_at,
    }
  }

  function mapMessage(message: MentorMessageDto): MentorMessage {
    return {
      id: message.id,
      sessionId: message.session_id,
      role: message.role,
      content: message.content,
      createdAt: message.created_at,
      inReplyToMessageId: message.in_reply_to_message_id,
    }
  }

  function mapMessagesPage(page: MentorMessagesPageDto): MentorMessagesPage {
    return { items: page.items.map(mapMessage), nextCursor: page.next_cursor }
  }

  function mapHint(hint: MentorContextHint | null | undefined) {
    return hint
      ? {
          goal_id: hint.goalId,
          skill_id: hint.skillId,
          competency_id: hint.competencyId,
          material_id: hint.materialId,
          activity_id: hint.activityId,
        }
      : null
  }
  function mapSnapshot(snapshot: MentorResponseSnapshotDto): MentorResponseSnapshot {
    return {
      attemptId: snapshot.attempt_id,
      learnerMessageId: snapshot.learner_message_id,
      status: snapshot.status,
      blocks: snapshot.blocks.map((block) => ({
        blockKey: block.block_key,
        ordinal: block.ordinal,
        intent: block.intent,
        content: block.content,
      })),
      consultations: snapshot.consultations,
      lastSequence: snapshot.last_sequence,
      failureCode: snapshot.failure_code,
      progress: snapshot.progress ?? null,
    }
  }
  function mapDetail(detail: MentorSessionDetailDto): MentorSessionDetail {
    return {
      session: mapSession(detail.session),
      messages: mapMessagesPage(detail.messages),
      pendingLearnerMessageId: detail.pending_learner_message_id,
      response: detail.response ? mapSnapshot(detail.response) : null,
    }
  }

  return {
    async submitMentorMessage(
      accessToken: string,
      sessionId: string,
      input: SubmitMentorMessageInput,
    ): Promise<MentorSessionDetail> {
      const response = await restClient.post<MentorSessionDetailDto>(
        `/intelligence/mentor-sessions/${encodeURIComponent(sessionId)}/messages`,
        {
          submission_key: input.submissionKey,
          content: input.content,
          context_hint: mapHint(input.contextHint),
        },
        auth(accessToken),
      )
      if (response.isFailure) response.throwError()
      return mapDetail(response.body)
    },
    async cancelMentorResponse(
      accessToken: string,
      sessionId: string,
      attemptId: string,
      submissionKey: string,
    ): Promise<MentorResponseSnapshot> {
      const response = await restClient.post<MentorResponseSnapshotDto>(
        `/intelligence/mentor-sessions/${encodeURIComponent(sessionId)}/responses/${encodeURIComponent(attemptId)}/cancel`,
        { submission_key: submissionKey },
        auth(accessToken),
      )
      if (response.isFailure) response.throwError()
      return mapSnapshot(response.body)
    },
    async retryMentorResponse(
      accessToken: string,
      sessionId: string,
      attemptId: string,
      submissionKey: string,
    ): Promise<MentorResponseSnapshot> {
      const response = await restClient.post<MentorResponseSnapshotDto>(
        `/intelligence/mentor-sessions/${encodeURIComponent(sessionId)}/responses/${encodeURIComponent(attemptId)}/retry`,
        { submission_key: submissionKey },
        auth(accessToken),
      )
      if (response.isFailure) response.throwError()
      return mapSnapshot(response.body)
    },
    async openMentorResponseEvents(
      accessToken: string,
      input: { sessionId: string; afterSequence: number },
      signal: AbortSignal,
    ): Promise<ReadableStream<Uint8Array>> {
      if (!streamClient)
        throw new AppError('Transporte da resposta indisponível.', 'Erro de configuração')
      const response = await streamClient.getStream(
        `/intelligence/mentor-sessions/${encodeURIComponent(input.sessionId)}/events`,
        {
          headers: {
            ...auth(accessToken).headers,
            Accept: 'text/event-stream',
            'Last-Event-ID': String(input.afterSequence),
          },
          signal,
        },
      )
      if (response.isFailure) response.throwError()
      return response.body
    },
    async startPlanning(
      accessToken: string,
      initialIntent: string,
    ): Promise<{ created_at: string; id: string }> {
      const response = await restClient.post<{ created_at: string; id: string }>(
        '/intelligence/planning-sessions',
        { initial_intent: initialIntent },
        auth(accessToken),
      )

      if (response.isFailure) response.throwError()

      return response.body
    },

    async createMentorSession(
      accessToken: string,
      input: CreateMentorSessionInput,
    ): Promise<MentorSessionDetail> {
      const response = await restClient.post<MentorSessionDetailDto>(
        '/intelligence/mentor-sessions',
        {
          submission_key: input.submissionKey,
          first_message: input.firstMessage,
          ...(input.contextHint ? { context_hint: mapHint(input.contextHint) } : {}),
        },
        auth(accessToken),
      )
      if (response.isFailure) response.throwError()
      return mapDetail(response.body)
    },

    async listMentorSessions(
      accessToken: string,
      input: { search?: string; cursor?: string },
    ): Promise<MentorSessionsPage> {
      const response = await restClient.get<MentorSessionsPageDto>(
        '/intelligence/mentor-sessions',
        { ...auth(accessToken), params: input },
      )
      if (response.isFailure) response.throwError()
      return {
        items: response.body.items.map(mapSession),
        nextCursor: response.body.next_cursor,
      }
    },

    async getMentorSession(
      accessToken: string,
      sessionId: string,
      cursor?: string,
    ): Promise<MentorSessionDetail> {
      const response = await restClient.get<MentorSessionDetailDto>(
        `/intelligence/mentor-sessions/${encodeURIComponent(sessionId)}`,
        { ...auth(accessToken), params: { cursor } },
      )
      if (response.isFailure) response.throwError()
      return mapDetail(response.body)
    },

    async renameMentorSession(
      accessToken: string,
      sessionId: string,
      title: string,
    ): Promise<MentorSession> {
      const response = await restClient.patch<MentorSessionDto>(
        `/intelligence/mentor-sessions/${encodeURIComponent(sessionId)}`,
        { title },
        auth(accessToken),
      )
      if (response.isFailure) response.throwError()
      return mapSession(response.body)
    },

    async removeMentorSession(accessToken: string, sessionId: string): Promise<void> {
      const response = await restClient.delete<void>(
        `/intelligence/mentor-sessions/${encodeURIComponent(sessionId)}`,
        undefined,
        auth(accessToken),
      )
      if (response.isFailure) response.throwError()
    },
  }
}
