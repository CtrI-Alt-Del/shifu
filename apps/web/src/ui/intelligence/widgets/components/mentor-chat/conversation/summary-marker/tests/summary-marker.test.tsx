import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useRef, useState } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { MentorSummaryMarker } from '@/core/intelligence/mentor-session-summary'
import { SummaryMarker } from '..'
import { useSummaryMarker } from '../use-summary-marker'

vi.mock('../use-summary-marker', () => ({ useSummaryMarker: vi.fn() }))

const useSummaryMarkerMock = vi.mocked(useSummaryMarker)
const handleRevealOriginalsMock = vi.fn()
const handleRetryMock = vi.fn()
const MARKER: MentorSummaryMarker = {
  version: 2,
  boundaryMessageId: '01J7T8AC91Z5K8M4JQ8C2D6F0B',
  coveredMessageCount: 21,
  completedAt: '2026-10-18T14:00:00Z',
  afterMessageId: null,
}
const SUMMARY_TEXT =
  'Nesta conversa, os assuntos foram range e lista. Você perguntou: “Meu laço não mostra o último item.”'

type SummaryMarkerView = Partial<ReturnType<typeof useSummaryMarker>>

// A stateful stand-in for the owning hook: it owns only the open flag, as the real
// hook does, so the primitive's focus management is exercised end to end.
function mockSummaryMarker(view: SummaryMarkerView = {}) {
  useSummaryMarkerMock.mockImplementation(() => {
    const [isOpen, setIsOpen] = useState(false)
    return {
      isOpen,
      summaryText: SUMMARY_TEXT,
      isLoadingSummary: false,
      hasSummaryError: false,
      rootRef: useRef<HTMLDivElement | null>(null),
      triggerRef: useRef<HTMLButtonElement | null>(null),
      handleOpenChange: setIsOpen,
      handleCloseAutoFocus: vi.fn(),
      handleRevealOriginals: async () => {
        handleRevealOriginalsMock()
        setIsOpen(false)
      },
      handleRetry: handleRetryMock,
      ...view,
    }
  })
}

describe('SummaryMarker', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockSummaryMarker()
  })
  afterEach(cleanup)

  it('renders the processing variant as a status with text and without a reading trigger', () => {
    render(<SummaryMarker variant='processing' />)

    expect(screen.getByRole('status')).toHaveTextContent('Resumindo contexto…')
    expect(screen.queryByRole('button', { name: 'Ver resumo' })).toBeNull()
  })

  it('renders the failed variant with its explanatory text and no action', () => {
    render(<SummaryMarker variant='failed' />)

    expect(
      screen.getByText(
        'Não foi possível resumir o contexto. O histórico completo continua disponível.',
      ),
    ).toBeVisible()
    expect(screen.queryByRole('button')).toBeNull()
  })

  it('renders the ready variant with a dialog trigger and no open dialog', () => {
    render(<SummaryMarker marker={MARKER} variant='ready' />)

    expect(screen.getByText('Contexto resumido')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Ver resumo' })).toHaveAttribute(
      'aria-haspopup',
      'dialog',
    )
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('opens the dialog by keyboard, moves focus into it and keeps focus trapped', async () => {
    const user = userEvent.setup()
    render(<SummaryMarker marker={MARKER} variant='ready' />)

    await user.tab()
    expect(screen.getByRole('button', { name: 'Ver resumo' })).toHaveFocus()
    await user.keyboard('{Enter}')

    const dialog = await screen.findByRole('dialog', { name: 'Resumo desta conversa' })
    expect(dialog).toHaveAccessibleDescription(
      'Suas mensagens originais continuam disponíveis.',
    )
    await waitFor(() =>
      expect(dialog).toContainElement(document.activeElement as HTMLElement),
    )
    expect(within(dialog).getByText(SUMMARY_TEXT)).toBeVisible()
    for (let step = 0; step < 6; step += 1) {
      await user.tab()
      expect(dialog).toContainElement(document.activeElement as HTMLElement)
    }
  })

  it.each([
    [
      'Escape',
      async (user: ReturnType<typeof userEvent.setup>) => user.keyboard('{Escape}'),
    ],
    [
      'the close button',
      async (user: ReturnType<typeof userEvent.setup>) =>
        user.click(screen.getByRole('button', { name: 'Fechar' })),
    ],
    [
      'Fechar resumo',
      async (user: ReturnType<typeof userEvent.setup>) =>
        user.click(screen.getByRole('button', { name: 'Fechar resumo' })),
    ],
  ])('closes with %s and returns focus to Ver resumo', async (_label, close) => {
    const user = userEvent.setup()
    render(<SummaryMarker marker={MARKER} variant='ready' />)
    const trigger = screen.getByRole('button', { name: 'Ver resumo' })

    await user.click(trigger)
    await screen.findByRole('dialog', { name: 'Resumo desta conversa' })
    await close(user)

    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
    await waitFor(() => expect(trigger).toHaveFocus())
  })

  it('closes the dialog and delegates revealing the original messages', async () => {
    const user = userEvent.setup()
    render(<SummaryMarker marker={MARKER} variant='ready' />)

    await user.click(screen.getByRole('button', { name: 'Ver resumo' }))
    await screen.findByRole('dialog', { name: 'Resumo desta conversa' })
    await user.click(screen.getByRole('button', { name: 'Ver mensagens originais' }))

    expect(handleRevealOriginalsMock).toHaveBeenCalledOnce()
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
  })

  it('shows a loading state with the original-messages action unavailable', async () => {
    mockSummaryMarker({ summaryText: null, isLoadingSummary: true })
    const user = userEvent.setup()
    render(<SummaryMarker marker={MARKER} variant='ready' />)

    await user.click(screen.getByRole('button', { name: 'Ver resumo' }))
    const dialog = await screen.findByRole('dialog', { name: 'Resumo desta conversa' })

    expect(within(dialog).getByRole('status')).toHaveTextContent('Carregando resumo…')
    expect(
      within(dialog).getByRole('button', { name: 'Ver mensagens originais' }),
    ).toBeDisabled()
  })

  it('shows a recoverable error state and retries the summary read', async () => {
    mockSummaryMarker({ summaryText: null, hasSummaryError: true })
    const user = userEvent.setup()
    render(<SummaryMarker marker={MARKER} variant='ready' />)

    await user.click(screen.getByRole('button', { name: 'Ver resumo' }))
    const dialog = await screen.findByRole('dialog', { name: 'Resumo desta conversa' })

    expect(within(dialog).getByRole('alert')).toHaveTextContent(
      'Não foi possível carregar o resumo.',
    )
    expect(
      within(dialog).getByRole('button', { name: 'Ver mensagens originais' }),
    ).toBeDisabled()
    await user.click(within(dialog).getByRole('button', { name: 'Tentar novamente' }))
    expect(handleRetryMock).toHaveBeenCalledOnce()
  })

  it('renders hostile summary text as plain text', async () => {
    const hostile = '<script>alert(1)</script>\n**negrito** [link](javascript:alert(1))'
    mockSummaryMarker({ summaryText: hostile })
    const user = userEvent.setup()
    render(<SummaryMarker marker={MARKER} variant='ready' />)

    await user.click(screen.getByRole('button', { name: 'Ver resumo' }))
    const dialog = await screen.findByRole('dialog', { name: 'Resumo desta conversa' })

    expect(dialog.querySelector('script')).toBeNull()
    expect(dialog.querySelector('a')).toBeNull()
    expect(dialog.querySelector('strong')).toBeNull()
    expect(dialog).toHaveTextContent('<script>alert(1)</script>')
    expect(dialog).toHaveTextContent('**negrito** [link](javascript:alert(1))')
  })
})
