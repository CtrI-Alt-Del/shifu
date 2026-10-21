import { act, cleanup, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { MentorContextValue } from '@/ui/intelligence/contexts/mentor-context/types'
import { useMentorContext } from '@/ui/intelligence/hooks/use-mentor-context'
import { useRenameSessionDialog } from '../use-rename-session-dialog'

vi.mock('@/ui/intelligence/hooks/use-mentor-context', () => ({
  useMentorContext: vi.fn(),
}))
const useMentorContextMock = vi.mocked(useMentorContext)

describe('useRenameSessionDialog', () => {
  afterEach(cleanup)

  it('validates Unicode code points and passes the trimmed title without truncating', () => {
    const renameSession = vi.fn()
    useMentorContextMock.mockReturnValue({
      activeDialog: 'rename',
      dialogSessionId: 'session-1',
      sessionsPage: {
        items: [
          {
            id: 'session-1',
            title: 'Atual',
            createdAt: '',
            updatedAt: '',
            lastActivityAt: '',
          },
        ],
        nextCursor: null,
      },
      renameSession,
    } as unknown as MentorContextValue)
    const { result } = renderHook(() => useRenameSessionDialog())
    act(() => result.current.setTitle(`${'😀'.repeat(121)}`))
    act(() =>
      result.current.handleSubmit({
        preventDefault: vi.fn(),
      } as unknown as React.FormEvent<HTMLFormElement>),
    )
    expect(result.current.validationError).toMatch('120')
    expect(renameSession).not.toHaveBeenCalled()
    act(() => result.current.setTitle('  Título válido  '))
    act(() =>
      result.current.handleSubmit({
        preventDefault: vi.fn(),
      } as unknown as React.FormEvent<HTMLFormElement>),
    )
    expect(renameSession).toHaveBeenCalledWith('Título válido')
  })
})
