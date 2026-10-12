import { useEffect, useRef } from 'react'
import { z } from 'zod'
import type {
  MentorResponseEvent,
  MentorResponseSnapshot,
} from '@/core/intelligence/mentor-response'

const STATUS = z.enum(['queued', 'processing', 'completed', 'failed', 'cancelled'])
const EVENT = z
  .object({
    session_id: z.string(),
    attempt_id: z.string(),
    sequence: z.number().int().nonnegative(),
    kind: z.enum(['status', 'consultation', 'block', 'completed', 'failed', 'cancelled']),
    status: STATUS,
    block: z
      .object({
        block_key: z.string(),
        ordinal: z.number().int().nonnegative(),
        intent: z.string().nullable(),
        content: z.string(),
      })
      .nullable(),
    consultation: z.enum(['learning', 'curriculum', 'gamification']).nullable(),
    progress: z.enum(['write-answer', 'review-answer']).nullish(),
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
              }
            : null,
          consultation: parsed.consultation,
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
