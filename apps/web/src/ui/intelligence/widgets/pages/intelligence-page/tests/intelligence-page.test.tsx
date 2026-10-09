import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { MentorChatProps } from '@/ui/intelligence/widgets/components/mentor-chat'
import { IntelligencePage } from '..'
import { useIntelligencePage } from '../use-intelligence-page'

vi.mock('../use-intelligence-page', () => ({ useIntelligencePage: vi.fn() }))
vi.mock('@/ui/intelligence/widgets/components/mentor-chat', () => ({
  MentorChat: ({ surface }: MentorChatProps) => <main>Mentor surface: {surface}</main>,
}))

const useIntelligencePageMock = vi.mocked(useIntelligencePage)

describe('IntelligencePage', () => {
  afterEach(cleanup)

  it('shows a polite route-loading status until a selected conversation is read', () => {
    useIntelligencePageMock.mockReturnValue({ isPageReady: false })
    render(<IntelligencePage />)
    expect(screen.getByText('Carregando conversa.')).toHaveAttribute(
      'aria-live',
      'polite',
    )
    expect(screen.queryByText('Mentor surface: page')).not.toBeInTheDocument()
  })

  it('renders the shared MentorChat page surface after route state is ready', () => {
    useIntelligencePageMock.mockReturnValue({ isPageReady: true })
    render(<IntelligencePage />)
    expect(screen.getByText('Mentor surface: page')).toBeVisible()
  })
})
