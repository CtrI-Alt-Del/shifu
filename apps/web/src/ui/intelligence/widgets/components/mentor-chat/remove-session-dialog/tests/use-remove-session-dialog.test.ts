import { cleanup, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { MentorContextValue } from '@/ui/intelligence/contexts/mentor-context/types'
import { useMentorContext } from '@/ui/intelligence/hooks/use-mentor-context'
import { useRemoveSessionDialog } from '../use-remove-session-dialog'

vi.mock('@/ui/intelligence/hooks/use-mentor-context', () => ({
  useMentorContext: vi.fn(),
}))
const useMentorContextMock = vi.mocked(useMentorContext)

describe('useRemoveSessionDialog', () => {
  afterEach(cleanup)

  it('resolves the selected row target independently of the open conversation', () => {
    useMentorContextMock.mockReturnValue({
      selectedSessionId: 'session-other',
      dialogSessionId: 'session-2',
      sessionsPage: {
        items: [
          {
            id: 'session-other',
            title: 'Atual',
            createdAt: '',
            updatedAt: '',
            lastActivityAt: '',
          },
          {
            id: 'session-2',
            title: 'Alvo da exclusão',
            createdAt: '',
            updatedAt: '',
            lastActivityAt: '',
          },
        ],
        nextCursor: null,
      },
    } as unknown as MentorContextValue)
    const { result } = renderHook(() => useRemoveSessionDialog())
    expect(result.current.session?.title).toBe('Alvo da exclusão')
  })
})
