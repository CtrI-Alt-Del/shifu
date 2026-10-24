import { useEffect, useRef } from 'react'
import { z } from 'zod'
import type {
  MentorResponseEvent,
  MentorResponseSnapshot,
} from '@/core/intelligence/mentor-response'
import { mapMentorActionProposal } from '@/rest/services/intelligence-service'

const STATUS = z.enum(['queued', 'processing', 'completed', 'failed', 'cancelled'])
const ACTION_PROPOSAL = z
  .object({
    id: z.string(),
    source_message_id: z.string(),
    kind: z.enum(['add_skill', 'remove_skill']),
    skill_id: z.string(),
    skill_name: z.string(),
    goal_id: z.string().nullable(),
    goal_title: z.string().nullable(),
    skill_experience_id: z.string().nullable(),
    candidate_goals: z.array(
      z
        .object({
          goal_id: z.string(),
          title: z.string(),
          contains_skill: z.boolean(),
          skill_experience_id: z.string().nullable(),
        })
        .strict(),
    ),
    justification: z.string().nullable(),
    status: z.enum(['pending', 'declined', 'completed', 'rejected']),
    outcome: z.enum(['added', 'already_present', 'removed']).nullable(),
    rejection_reason: z
      .enum(['goal_unavailable', 'skill_unavailable', 'experience_unavailable'])
      .nullable(),
    resolved_goal_id: z.string().nullable(),
    resolved_skill_experience_id: z.string().nullable(),
    created_at: z.string(),
  })
  .strict()
const EVENT = z
  .object({
    session_id: z.string(),
    attempt_id: z.string(),
    sequence: z.number().int().nonnegative(),
    kind: z.enum([
      'status',
      'consultation',
      'block',
      'completed',
      'failed',
      'cancelled',
      'action',
    ]),
    status: STATUS,
    block: z
      .object({
        block_key: z.string(),
        ordinal: z.number().int().nonnegative(),
        intent: z.string().nullable(),
        content: z.string(),
        sources: z
          .array(
            z
              .object({
                attachment_id: z.string(),
                chunk_id: z.string(),
                page_number: z.number().int().positive().nullable(),
                locator: z.string(),
              })
              .strict(),
          )
          .optional()
          .default([]),
      })
      .nullable(),
    consultation: z.enum(['learning', 'curriculum', 'gamification']).nullable(),
    action_proposal: ACTION_PROPOSAL.nullish(),
    progress: z.enum(['summarize-context', 'write-answer', 'review-answer']).nullish(),
    failure_code: z.string().nullable(),
    created_at: z.string(),
  })
  .strict()
export type UseMentorResponseStreamInput = {
  sessionId: string | null
  attemptId: string | null
  enabled: boolean
  afterSequence: number
  openEventSource(sessionId: string, afterSequence: number): EventSource
  onEvent(event: MentorResponseEvent): void
  reconcile(): Promise<MentorResponseSnapshot | null>
  onUnavailable(): void
}
export function useMentorResponseStream(input: UseMentorResponseStreamInput): void {
  const latest = useRef(input)
  latest.current = input
  const { sessionId, attemptId, enabled } = input
  useEffect(() => {
    if (!enabled || !sessionId || !attemptId) return
    let disposed = false
    let generation = 0
    let cursor = latest.current.afterSequence
    let source: EventSource | null = null
    let reconciling = false
    function close() {
      generation += 1
      source?.close()
      source = null
    }
    async function recover() {
      if (disposed || reconciling) return
      close()
      reconciling = true
      const currentGeneration = generation
      try {
        const snapshot = await latest.current.reconcile()
        if (disposed || generation !== currentGeneration) return
        if (
          !snapshot ||
          snapshot.attemptId !== attemptId ||
          !['queued', 'processing'].includes(snapshot.status)
        )
          return
        cursor = Math.max(cursor, snapshot.lastSequence)
        open()
      } catch {
        if (!disposed && generation === currentGeneration) latest.current.onUnavailable()
      } finally {
        reconciling = false
      }
    }
    function open() {
      if (disposed) return
      const currentGeneration = ++generation
      source = latest.current.openEventSource(sessionId as string, cursor)
      source.addEventListener('mentor.response', (event) => {
        if (disposed || generation !== currentGeneration) return
        let parsed: z.infer<typeof EVENT>
        try {
          parsed = EVENT.parse(JSON.parse((event as MessageEvent<string>).data))
        } catch {
          void recover()
          return
        }
        if (
          parsed.session_id !== sessionId ||
          parsed.attempt_id !== attemptId ||
          parsed.sequence <= cursor
        )
          return
        cursor = parsed.sequence
        latest.current.onEvent({
          sessionId: parsed.session_id,
          attemptId: parsed.attempt_id,
          sequence: parsed.sequence,
          kind: parsed.kind,
          status: parsed.status,
          block: parsed.block
            ? {
                blockKey: parsed.block.block_key,
                ordinal: parsed.block.ordinal,
                intent: parsed.block.intent,
                content: parsed.block.content,
                sources: parsed.block.sources.map((source) => ({
                  attachmentId: source.attachment_id,
                  chunkId: source.chunk_id,
                  pageNumber: source.page_number,
                  locator: source.locator,
                })),
              }
            : null,
          consultation: parsed.consultation,
          actionProposal: parsed.action_proposal
            ? mapMentorActionProposal(parsed.action_proposal)
            : null,
          progress: parsed.progress ?? null,
          failureCode: parsed.failure_code,
          createdAt: parsed.created_at,
        })
        if (['completed', 'failed', 'cancelled'].includes(parsed.status)) close()
      })
      source.addEventListener('error', () => {
        if (!disposed && generation === currentGeneration) void recover()
      })
    }
    open()
    return () => {
      disposed = true
      close()
    }
  }, [sessionId, attemptId, enabled])
}
