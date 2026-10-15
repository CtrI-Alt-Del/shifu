import { act, cleanup, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { useMentorResponseStream } from '../use-mentor-response-stream'

describe('useMentorResponseStream', () => {
  afterEach(cleanup)

  it('defaults old block events to no sources and maps structured source fields', () => {
    const source = Object.assign(new EventTarget(), {
      close: vi.fn(),
    }) as unknown as EventSource
    const onEvent = vi.fn()
    const { unmount } = renderHook(() =>
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
})
