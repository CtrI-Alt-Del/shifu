import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { MentorChatProps } from '@/ui/intelligence/widgets/components/mentor-chat'
import { MentorFab } from '..'
import { useMentorFab } from '../use-mentor-fab'

vi.mock('../use-mentor-fab', () => ({ useMentorFab: vi.fn() }))
vi.mock('@/ui/intelligence/widgets/components/mentor-chat', () => ({
  MentorChat: ({ surface }: MentorChatProps) => <div>Mentor surface: {surface}</div>,
}))

const useMentorFabMock = vi.mocked(useMentorFab)
const openPanelMock = vi.fn()
const closePanelMock = vi.fn()

describe('MentorFab', () => {
  afterEach(cleanup)

  it('opens the shared Mentor panel from the floating action', () => {
    useMentorFabMock.mockReturnValue({
      closePanel: closePanelMock,
      handlePanelKeyDown: vi.fn(),
      isPanelOpen: false,
      openPanel: openPanelMock,
      panelRef: { current: null },
      triggerRef: { current: null },
    })
    render(<MentorFab />)
    fireEvent.click(screen.getByRole('button', { name: 'Abrir Mentor' }))
    expect(openPanelMock).toHaveBeenCalledOnce()
    expect(
      screen.queryByRole('dialog', { name: 'Painel do Mentor' }),
    ).not.toBeInTheDocument()
  })

  it('renders the same MentorChat composition and closes the panel accessibly', () => {
    useMentorFabMock.mockReturnValue({
      closePanel: closePanelMock,
      handlePanelKeyDown: vi.fn(),
      isPanelOpen: true,
      openPanel: openPanelMock,
      panelRef: { current: null },
      triggerRef: { current: null },
    })
    render(<MentorFab />)
    expect(screen.getByRole('dialog', { name: 'Painel do Mentor' })).toBeVisible()
    expect(screen.getByText('Mentor surface: fab')).toBeVisible()
    expect(
      screen.queryByRole('button', { name: 'Fechar Mentor' }),
    ).not.toBeInTheDocument()
    expect(screen.getByLabelText('Fechar Mentor')).not.toBeVisible()
  })
  it.each([false, true])(
    'omits floating access on the dedicated Mentor page (panel open: %s)',
    (isPanelOpen) => {
      useMentorFabMock.mockReturnValue({
        closePanel: closePanelMock,
        handlePanelKeyDown: vi.fn(),
        isPanelOpen,
        openPanel: openPanelMock,
        panelRef: { current: null },
        triggerRef: { current: null },
      })
      const { container } = render(<MentorFab isMentorPage />)
      expect(container).toBeEmptyDOMElement()
    },
  )
})
