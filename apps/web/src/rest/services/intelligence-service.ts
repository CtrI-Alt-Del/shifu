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
}

export type CreateMentorSessionInput = {
  submissionKey: string
  firstMessage: string
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
}

export type IntelligenceService = ReturnType<typeof IntelligenceService>

export const IntelligenceService = (restClient: RestClient) => {
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

  function mapDetail(detail: MentorSessionDetailDto): MentorSessionDetail {
    return {
      session: mapSession(detail.session),
      messages: mapMessagesPage(detail.messages),
      pendingLearnerMessageId: detail.pending_learner_message_id,
    }
  }

  return {
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
