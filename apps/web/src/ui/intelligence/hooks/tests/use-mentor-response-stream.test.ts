import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, renderHook } from '@testing-library/react'
import { createElement, type ReactNode } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AI_QUOTA_USAGE_QUERY_KEY } from '../ai-quota-usage-query-key'
import { useMentorResponseStream } from '../use-mentor-response-stream'

function createWrapper(queryClient: QueryClient) {
  return ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children)
}

describe('useMentorResponseStream', () => {
  afterEach(cleanup)

  it('defaults old block events to no sources and maps structured source fields', () => {
    const source = Object.assign(new EventTarget(), {
      close: vi.fn(),
    }) as unknown as EventSource
    const onEvent = vi.fn()
    const queryClient = new QueryClient()
    const { unmount } = renderHook(
      () =>
        useMentorResponseStream({
          sessionId: 'session-1',
          attemptId: 'attempt-1',
          enabled: true,
          afterSequence: 0,
          openEventSource: vi.fn(() => source),
          onEvent,
          reconcile: vi.fn(async () => null),
          onUnavailable: vi.fn(),
        }),
      { wrapper: createWrapper(queryClient) },
    )

    act(() =>
      source.dispatchEvent(
        new MessageEvent('mentor.response', {
          data: JSON.stringify({
            session_id: 'session-1',
            attempt_id: 'attempt-1',
            sequence: 1,
            kind: 'block',
            status: 'processing',
            block: {
              block_key: 'old-block',
              ordinal: 0,
              intent: null,
              content: 'Resposta antiga',
            },
            consultation: null,
            progress: null,
            failure_code: null,
            created_at: '2026-10-14T12:00:00Z',
          }),
        }),
      ),
    )
    act(() =>
      source.dispatchEvent(
        new MessageEvent('mentor.response', {
          data: JSON.stringify({
            session_id: 'session-1',
            attempt_id: 'attempt-1',
            sequence: 2,
            kind: 'block',
            status: 'processing',
            block: {
              block_key: 'sourced-block',
              ordinal: 1,
              intent: null,
              content: 'Resposta com fonte',
              sources: [
                {
                  attachment_id: 'attachment-1',
                  chunk_id: 'chunk-1',
                  page_number: 3,
                  locator: 'Exemplo resolvido',
                },
              ],
            },
            consultation: null,
            progress: null,
            failure_code: null,
            created_at: '2026-10-14T12:00:01Z',
          }),
        }),
      ),
    )

    expect(onEvent).toHaveBeenNthCalledWith(
      1,
      expect.objectContaining({
        block: expect.objectContaining({ blockKey: 'old-block', sources: [] }),
      }),
    )
    expect(onEvent).toHaveBeenNthCalledWith(
      2,
      expect.objectContaining({
        block: {
          blockKey: 'sourced-block',
          ordinal: 1,
          intent: null,
          content: 'Resposta com fonte',
          sources: [
            {
              attachmentId: 'attachment-1',
              chunkId: 'chunk-1',
              pageNumber: 3,
              locator: 'Exemplo resolvido',
            },
          ],
        },
      }),
    )

    unmount()
  })

  it('refreshes the quota reading only when the response reaches a terminal event', () => {
    const source = Object.assign(new EventTarget(), {
      close: vi.fn(),
    }) as unknown as EventSource
    const queryClient = new QueryClient()
    const invalidateQueriesSpy = vi.spyOn(queryClient, 'invalidateQueries')
    const { unmount } = renderHook(
      () =>
        useMentorResponseStream({
          sessionId: 'session-1',
          attemptId: 'attempt-1',
          enabled: true,
          afterSequence: 0,
          openEventSource: vi.fn(() => source),
          onEvent: vi.fn(),
          reconcile: vi.fn(async () => null),
          onUnavailable: vi.fn(),
        }),
      { wrapper: createWrapper(queryClient) },
    )
    const dispatchEvent = (sequence: number, kind: string, status: string) =>
      act(() => {
        source.dispatchEvent(
          new MessageEvent('mentor.response', {
            data: JSON.stringify({
              session_id: 'session-1',
              attempt_id: 'attempt-1',
              sequence,
              kind,
              status,
              block: null,
              consultation: null,
              progress: null,
              failure_code: null,
              created_at: '2026-10-14T12:00:00Z',
            }),
          }),
        )
      })

    dispatchEvent(1, 'status', 'processing')
    expect(invalidateQueriesSpy).not.toHaveBeenCalled()

    dispatchEvent(2, 'completed', 'completed')
    expect(invalidateQueriesSpy).toHaveBeenCalledWith({
      queryKey: AI_QUOTA_USAGE_QUERY_KEY,
    })

    unmount()
  })

  it('refreshes the quota reading when a dropped stream reconciles to a terminal snapshot', async () => {
    const source = Object.assign(new EventTarget(), {
      close: vi.fn(),
    }) as unknown as EventSource
    const queryClient = new QueryClient()
    const invalidateQueriesSpy = vi.spyOn(queryClient, 'invalidateQueries')
    const snapshot = {
      attemptId: 'attempt-1',
      learnerMessageId: 'learner-1',
      status: 'processing' as 'processing' | 'completed',
      blocks: [],
      consultations: [],
      lastSequence: 3,
      failureCode: null,
    }
    const reconcile = vi.fn(async () => snapshot)
    const { unmount } = renderHook(
      () =>
        useMentorResponseStream({
          sessionId: 'session-1',
          attemptId: 'attempt-1',
          enabled: true,
          afterSequence: 0,
          openEventSource: vi.fn(() => source),
          onEvent: vi.fn(),
          reconcile,
          onUnavailable: vi.fn(),
        }),
      { wrapper: createWrapper(queryClient) },
    )

    await act(async () => {
      source.dispatchEvent(new Event('error'))
    })
    expect(reconcile).toHaveBeenCalledOnce()
    expect(invalidateQueriesSpy).not.toHaveBeenCalled()

    snapshot.status = 'completed'
    await act(async () => {
      source.dispatchEvent(new Event('error'))
    })

    expect(reconcile).toHaveBeenCalledTimes(2)
    expect(invalidateQueriesSpy).toHaveBeenCalledWith({
      queryKey: AI_QUOTA_USAGE_QUERY_KEY,
    })

    unmount()
  })
})
