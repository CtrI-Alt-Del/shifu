import { AppError } from '@/core/errors/app-error'
import type { RestStreamClient } from '@/core/shared/interfaces/rest-stream-client'
import type { MentorActionProposal } from '@/core/intelligence/mentor-action-proposal'
import type {
  MentorContextHint,
  MentorResponseSnapshot,
  MentorResponseStatus,
  SubmitMentorMessageInput,
} from '@/core/intelligence/mentor-response'
import type {
  MentorAttachment,
  MentorAttachmentBatch,
  MentorAttachmentSource,
} from '@/core/intelligence/mentor-attachment'
import type {
  PlanningAnswersSubmission,
  PlanningOperation,
  PlanningQuestion,
  PlanningSession,
  PlanningGoalCreation,
} from '@/core/intelligence/planning-session'
import type {
  EditLearnerMemoryInput,
  LearnerMemory,
  LearnerMemoryCategory,
  ListLearnerMemoriesInput,
  MentorConversationMemoryItem,
} from '@/core/intelligence/learner-memory'
import type {
  MentorSessionSummaryContent,
  MentorSessionSummaryState,
} from '@/core/intelligence/mentor-session-summary'
import type { RestClient } from '@/core/shared/interfaces/rest-client'
import type { RestResponse } from '@/core/shared/responses/rest-response'

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
  attachments: MentorAttachment[]
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
  summary: MentorSessionSummaryState
  memoryItems: MentorConversationMemoryItem[]
  actionItems: MentorActionProposal[]
}

export type CreateMentorSessionInput = {
  submissionKey: string
  firstMessage: string
  contextHint?: MentorContextHint | null
  attachmentBatchId?: string
  attachmentIds?: string[]
}

type MentorAttachmentDto = {
  attachment_id: string
  filename: string
  media_type: string
  size_bytes: number
  status: MentorAttachment['status']
  failure_code: string | null
  analyzed_pages: number[]
  illegible_pages: number[]
  uninterpreted_pages: number[]
}

type MentorAttachmentBatchDto = {
  batch_id: string
  expires_at: string
  attachments: MentorAttachmentDto[]
}

type MentorAttachmentBatchCreatedDto = Pick<
  MentorAttachmentBatchDto,
  'batch_id' | 'expires_at'
>

type MentorAttachmentSourceDto = {
  attachment_id: string
  chunk_id: string
  page_number: number | null
  locator: string
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
  attachments?: MentorAttachmentDto[]
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
  summary?: MentorSessionSummaryStateDto
  memory_items?: MentorConversationMemoryItemDto[]
  action_items?: MentorActionProposalDto[]
}

export type MentorActionProposalDto = {
  id: string
  source_message_id: string
  kind: MentorActionProposal['kind']
  skill_id: string
  skill_name: string
  goal_id: string | null
  goal_title: string | null
  skill_experience_id: string | null
  candidate_goals: {
    goal_id: string
    title: string
    contains_skill: boolean
    skill_experience_id: string | null
  }[]
  justification: string | null
  status: MentorActionProposal['status']
  outcome: MentorActionProposal['outcome']
  rejection_reason: MentorActionProposal['rejectionReason']
  resolved_goal_id: string | null
  resolved_skill_experience_id: string | null
  created_at: string
}

type MentorConversationMemoryItemDto = {
  id: string
  source_message_id: string
  kind: 'created' | 'updated'
  category: LearnerMemoryCategory
  memory_id: string | null
  content: string | null
  previous_content: string | null
  created_at: string
}

type LearnerMemoryDto = {
  id: string
  category: LearnerMemoryCategory
  content: string
  version: number
  created_at: string
  updated_at: string
  origins: {
    session_id: string
    message_id: string | null
    conversation_title: string | null
    is_available: boolean
    declared_at: string
  }[]
  concepts: { key: string; label: string }[]
}

type LearnerMemoriesDto = { items: LearnerMemoryDto[] }

type MentorSessionSummaryStateDto = {
  current: {
    version: number
    boundary_message_id: string
    covered_message_count: number
    completed_at: string
    after_message_id?: string | null
  } | null
  failure_after_message_id: string | null
}

type MentorSessionSummaryContentDto = {
  version: number
  text: string
  covered_message_count: number
  first_message_id: string
}

type MentorResponseSnapshotDto = {
  progress?: MentorResponseSnapshot['progress']
  attempt_id: string
  learner_message_id: string
  status: MentorResponseStatus
  blocks: {
    block_key: string
    ordinal: number
    intent: string | null
    content: string
    sources?: MentorAttachmentSourceDto[]
  }[]
  consultations: string[]
  last_sequence: number
  failure_code: string | null
}
type PlanningSessionDto = {
  id: string
  status: PlanningSession['status']
  intent: string
  generation: number
  created_at: string
  updated_at: string
  operation: {
    kind: PlanningOperation['kind']
    started_at: string
    stage?: PlanningOperation['stage']
  } | null
  consulted_curriculum: boolean
  batch: {
    id: string
    questions: {
      id: string
      text: string
      kind: PlanningQuestion['kind']
      options: { id: string; text: string; exclusive: boolean }[]
    }[]
  } | null
  answered_batch_count: number
  proposal: {
    title: string
    description: string
    skills: { skill_id: string; name: string; justification: string }[]
    relations: { skill_id: string; foundation_skill_id: string }[]
  } | null
  message: string | null
  failure_code: string | null
}

export function mapMentorActionProposal(
  proposal: MentorActionProposalDto,
): MentorActionProposal {
  return {
    id: proposal.id,
    sourceMessageId: proposal.source_message_id,
    kind: proposal.kind,
    skillId: proposal.skill_id,
    skillName: proposal.skill_name,
    goalId: proposal.goal_id,
    goalTitle: proposal.goal_title,
    skillExperienceId: proposal.skill_experience_id,
    candidateGoals: proposal.candidate_goals.map((candidate) => ({
      goalId: candidate.goal_id,
      title: candidate.title,
      containsSkill: candidate.contains_skill,
      skillExperienceId: candidate.skill_experience_id,
    })),
    justification: proposal.justification,
    status: proposal.status,
    outcome: proposal.outcome,
    rejectionReason: proposal.rejection_reason,
    resolvedGoalId: proposal.resolved_goal_id,
    resolvedSkillExperienceId: proposal.resolved_skill_experience_id,
    createdAt: proposal.created_at,
  }
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
      attachments: (message.attachments ?? []).map(mapAttachment),
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
  function mapAttachment(attachment: MentorAttachmentDto): MentorAttachment {
    return {
      attachmentId: attachment.attachment_id,
      filename: attachment.filename,
      mediaType: attachment.media_type,
      sizeBytes: attachment.size_bytes,
      status: attachment.status,
      failureCode: attachment.failure_code,
      analyzedPages: attachment.analyzed_pages,
      illegiblePages: attachment.illegible_pages,
      uninterpretedPages: attachment.uninterpreted_pages,
    }
  }
  function mapAttachmentSource(
    source: MentorAttachmentSourceDto,
  ): MentorAttachmentSource {
    return {
      attachmentId: source.attachment_id,
      chunkId: source.chunk_id,
      pageNumber: source.page_number,
      locator: source.locator,
    }
  }
  function mapAttachmentBatch(batch: MentorAttachmentBatchDto): MentorAttachmentBatch {
    return {
      batchId: batch.batch_id,
      expiresAt: batch.expires_at,
      attachments: batch.attachments.map(mapAttachment),
    }
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
        sources: (block.sources ?? []).map(mapAttachmentSource),
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
      summary: mapSummaryState(detail.summary),
      memoryItems: (detail.memory_items ?? []).map(mapMemoryItem),
      actionItems: (detail.action_items ?? []).map(mapMentorActionProposal),
    }
  }
  function mapMemoryItem(
    item: MentorConversationMemoryItemDto,
  ): MentorConversationMemoryItem {
    return {
      id: item.id,
      sourceMessageId: item.source_message_id,
      kind: item.kind,
      category: item.category,
      memoryId: item.memory_id,
      content: item.content,
      previousContent: item.previous_content,
      createdAt: item.created_at,
    }
  }
  function mapLearnerMemory(memory: LearnerMemoryDto): LearnerMemory {
    return {
      id: memory.id,
      category: memory.category,
      content: memory.content,
      version: memory.version,
      createdAt: memory.created_at,
      updatedAt: memory.updated_at,
      origins: memory.origins.map((origin) => ({
        sessionId: origin.session_id,
        messageId: origin.message_id,
        conversationTitle: origin.conversation_title,
        isAvailable: origin.is_available,
        declaredAt: origin.declared_at,
      })),
      concepts: memory.concepts.map((concept) => ({
        key: concept.key,
        label: concept.label,
      })),
    }
  }
  function mapSummaryState(
    summary: MentorSessionSummaryStateDto | undefined,
  ): MentorSessionSummaryState {
    return {
      current: summary?.current
        ? {
            version: summary.current.version,
            boundaryMessageId: summary.current.boundary_message_id,
            coveredMessageCount: summary.current.covered_message_count,
            completedAt: summary.current.completed_at,
            afterMessageId: summary.current.after_message_id ?? null,
          }
        : null,
      failureAfterMessageId: summary?.failure_after_message_id ?? null,
    }
  }
  function mapPlanningSession(session: PlanningSessionDto): PlanningSession {
    return {
      id: session.id,
      status: session.status,
      intent: session.intent,
      generation: session.generation,
      createdAt: session.created_at,
      updatedAt: session.updated_at,
      operation: session.operation
        ? {
            kind: session.operation.kind,
            startedAt: session.operation.started_at,
            stage: session.operation.stage ?? null,
          }
        : null,
      consultedCurriculum: session.consulted_curriculum,
      batch: session.batch
        ? {
            id: session.batch.id,
            questions: session.batch.questions.map((question) => ({
              id: question.id,
              text: question.text,
              kind: question.kind,
              options: question.options.map((option) => ({
                id: option.id,
                text: option.text,
                exclusive: option.exclusive,
              })),
            })),
          }
        : null,
      answeredBatchCount: session.answered_batch_count,
      proposal: session.proposal
        ? {
            title: session.proposal.title,
            description: session.proposal.description,
            skills: session.proposal.skills.map((skill) => ({
              skillId: skill.skill_id,
              name: skill.name,
              justification: skill.justification,
            })),
            relations: session.proposal.relations.map((relation) => ({
              skillId: relation.skill_id,
              foundationSkillId: relation.foundation_skill_id,
            })),
          }
        : null,
      message: session.message,
      failureCode: session.failure_code,
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
          ...(input.attachmentBatchId
            ? { attachment_batch_id: input.attachmentBatchId }
            : {}),
          ...(input.attachmentIds?.length ? { attachment_ids: input.attachmentIds } : {}),
        },
        auth(accessToken),
      )
      if (response.isFailure) response.throwError()
      return mapDetail(response.body)
    },
    async createMentorAttachmentBatch(
      accessToken: string,
      sessionId?: string | null,
    ): Promise<MentorAttachmentBatch> {
      const response = await restClient.post<MentorAttachmentBatchCreatedDto>(
        '/intelligence/mentor-attachment-batches',
        sessionId ? { session_id: sessionId } : {},
        auth(accessToken),
      )
      if (response.isFailure) response.throwError()
      return {
        batchId: response.body.batch_id,
        expiresAt: response.body.expires_at,
        attachments: [],
      }
    },
    async uploadMentorAttachment(
      accessToken: string,
      batchId: string,
      uploadKey: string,
      file: File,
      signal?: AbortSignal,
    ): Promise<{ attachment: MentorAttachment; statusCode: number }> {
      const formData = new FormData()
      formData.append('file', file, file.name)
      formData.append('upload_key', uploadKey)
      const response = await restClient.postFormData<MentorAttachmentDto>(
        `/intelligence/mentor-attachment-batches/${encodeURIComponent(batchId)}/attachments`,
        formData,
        { ...auth(accessToken), signal },
      )
      if (response.isFailure) response.throwError()
      return { attachment: mapAttachment(response.body), statusCode: response.statusCode }
    },
    async getMentorAttachmentBatch(
      accessToken: string,
      batchId: string,
    ): Promise<MentorAttachmentBatch> {
      const response = await restClient.get<MentorAttachmentBatchDto>(
        `/intelligence/mentor-attachment-batches/${encodeURIComponent(batchId)}`,
        auth(accessToken),
      )
      if (response.isFailure) response.throwError()
      return mapAttachmentBatch(response.body)
    },
    async removeMentorAttachment(
      accessToken: string,
      batchId: string,
      attachmentId: string,
    ): Promise<void> {
      const response = await restClient.delete<void>(
        `/intelligence/mentor-attachment-batches/${encodeURIComponent(batchId)}/attachments/${encodeURIComponent(attachmentId)}`,
        undefined,
        auth(accessToken),
      )
      if (response.isFailure) response.throwError()
    },
    async readMentorAttachmentFile(
      accessToken: string,
      sessionId: string,
      attachmentId: string,
      preview: boolean,
      signal?: AbortSignal,
    ): Promise<RestResponse<Blob>> {
      const response = await restClient.getFile(
        `/intelligence/mentor-sessions/${encodeURIComponent(sessionId)}/attachments/${encodeURIComponent(attachmentId)}/file`,
        { ...auth(accessToken), params: { preview }, signal },
      )
      if (response.isFailure) response.throwError()
      return response
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
    async declineMentorActionProposal(
      accessToken: string,
      sessionId: string,
      proposalId: string,
    ): Promise<MentorActionProposal> {
      const response = await restClient.post<MentorActionProposalDto>(
        `/intelligence/mentor-sessions/${encodeURIComponent(sessionId)}/action-proposals/${encodeURIComponent(proposalId)}/decline`,
        undefined,
        auth(accessToken),
      )
      if (response.isFailure) response.throwError()
      return mapMentorActionProposal(response.body)
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
    async getPlanningSession(
      accessToken: string,
      planningId: string,
    ): Promise<PlanningSession> {
      const response = await restClient.get<PlanningSessionDto>(
        `/intelligence/planning-sessions/${planningId}`,
        auth(accessToken),
      )
      if (response.isFailure) response.throwError()
      return mapPlanningSession(response.body)
    },
    async answerPlanningQuestions(
      accessToken: string,
      planningId: string,
      submission: PlanningAnswersSubmission,
    ): Promise<PlanningSession> {
      const response = await restClient.post<PlanningSessionDto>(
        `/intelligence/planning-sessions/${planningId}/answers`,
        {
          batch_id: submission.batchId,
          answers: submission.answers.map((answer) => ({
            question_id: answer.questionId,
            option_ids: answer.optionIds,
          })),
        },
        auth(accessToken),
      )
      if (response.isFailure) response.throwError()
      return mapPlanningSession(response.body)
    },
    async restartPlanning(
      accessToken: string,
      planningId: string,
      initialIntent: string,
    ): Promise<PlanningSession> {
      const response = await restClient.post<PlanningSessionDto>(
        `/intelligence/planning-sessions/${planningId}/restart`,
        { initial_intent: initialIntent },
        auth(accessToken),
      )
      if (response.isFailure) response.throwError()
      return mapPlanningSession(response.body)
    },
    async confirmPlanning(
      accessToken: string,
      planningId: string,
      input: { confirmationKey: string; title: string; description: string },
    ): Promise<PlanningGoalCreation> {
      const response = await restClient.post<{ goal_id: string; replayed: boolean }>(
        `/intelligence/planning-sessions/${planningId}/confirm`,
        {
          confirmation_key: input.confirmationKey,
          title: input.title,
          description: input.description,
        },
        auth(accessToken),
      )
      if (response.isFailure) response.throwError()
      return { goalId: response.body.goal_id, replayed: response.body.replayed }
    },
    async retryPlanning(
      accessToken: string,
      planningId: string,
    ): Promise<PlanningSession> {
      const response = await restClient.post<PlanningSessionDto>(
        `/intelligence/planning-sessions/${planningId}/retry`,
        undefined,
        auth(accessToken),
      )
      if (response.isFailure) response.throwError()
      return mapPlanningSession(response.body)
    },
    async cancelPlanning(accessToken: string, planningId: string): Promise<void> {
      const response = await restClient.delete<void>(
        `/intelligence/planning-sessions/${planningId}`,
        undefined,
        auth(accessToken),
      )
      if (response.isFailure) response.throwError()
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
          ...(input.attachmentBatchId
            ? { attachment_batch_id: input.attachmentBatchId }
            : {}),
          ...(input.attachmentIds?.length ? { attachment_ids: input.attachmentIds } : {}),
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

    async getMentorSessionSummary(
      accessToken: string,
      sessionId: string,
    ): Promise<MentorSessionSummaryContent> {
      const response = await restClient.get<MentorSessionSummaryContentDto>(
        `/intelligence/mentor-sessions/${encodeURIComponent(sessionId)}/summary`,
        auth(accessToken),
      )
      if (response.isFailure) response.throwError()
      return {
        version: response.body.version,
        text: response.body.text,
        coveredMessageCount: response.body.covered_message_count,
        firstMessageId: response.body.first_message_id,
      }
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

    async listLearnerMemories(
      accessToken: string,
      input: ListLearnerMemoriesInput,
    ): Promise<LearnerMemory[]> {
      const response = await restClient.get<LearnerMemoriesDto>(
        '/intelligence/learner-memories',
        { ...auth(accessToken), params: { q: input.q, category: input.category } },
      )
      if (response.isFailure) response.throwError()
      return response.body.items.map(mapLearnerMemory)
    },

    async getLearnerMemory(
      accessToken: string,
      memoryId: string,
    ): Promise<LearnerMemory> {
      const response = await restClient.get<LearnerMemoryDto>(
        `/intelligence/learner-memories/${memoryId}`,
        auth(accessToken),
      )
      if (response.isFailure) response.throwError()
      return mapLearnerMemory(response.body)
    },

    async editLearnerMemory(
      accessToken: string,
      memoryId: string,
      input: EditLearnerMemoryInput,
    ): Promise<LearnerMemory> {
      const response = await restClient.patch<LearnerMemoryDto>(
        `/intelligence/learner-memories/${memoryId}`,
        { content: input.content, expected_version: input.expectedVersion },
        auth(accessToken),
      )
      if (response.isFailure) response.throwError()
      return mapLearnerMemory(response.body)
    },

    async removeLearnerMemory(accessToken: string, memoryId: string): Promise<void> {
      const response = await restClient.delete<void>(
        `/intelligence/learner-memories/${memoryId}`,
        undefined,
        auth(accessToken),
      )
      if (response.isFailure) response.throwError()
    },
  }
}
