import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { SessionHistory } from '..'
import { useSessionHistory } from '../use-session-history'

vi.mock('../use-session-history', () => ({ useSessionHistory: vi.fn() }))
const useSessionHistoryMock = vi.mocked(useSessionHistory)
const selectSessionMock = vi.fn()
const setSearchMock = vi.fn()
const openRenameMock = vi.fn()
const openRemoveMock = vi.fn()

describe('SessionHistory', () => {
  afterEach(cleanup)

  it('searches titles, identifies the selected conversation and exposes row actions', () => {
    const historyState = {
      historyError: null,
      isReadingHistory: false,
      loadMoreSessions: vi.fn(),
      loadSentinelRef: { current: null },
      openRemoveDialog: openRemoveMock,
      openRenameDialog: openRenameMock,
      search: '',
      selectSession: selectSessionMock,
      selectedSessionId: 'session-1',
      sessionsPage: {
        items: [
          {
            id: 'session-1',
            title: 'Prática de Python',
            createdAt: '2026-10-09T12:00:00Z',
            updatedAt: '2026-10-09T12:00:00Z',
            lastActivityAt: '2026-10-09T12:00:00Z',
          },
          {
            id: 'session-2',
            title: 'Revisão de lógica',
            createdAt: '2026-10-09T12:00:00Z',
            updatedAt: '2026-10-09T12:00:00Z',
            lastActivityAt: '2026-10-09T12:00:00Z',
          },
        ],
        nextCursor: null,
      },
      setSearch: setSearchMock,
      refresh: vi.fn(),
    } as unknown as ReturnType<typeof useSessionHistory>
    useSessionHistoryMock.mockReturnValue(historyState)
    const { rerender } = render(<SessionHistory />)
    fireEvent.change(screen.getByLabelText('Buscar conversa por título'), {
      target: { value: 'python' },
    })
    expect(setSearchMock).toHaveBeenCalledWith('python')
    const rows = screen.getAllByRole('listitem')
    const sessionRow = within(rows[0])
    expect(
      sessionRow.getByRole('button', { name: /conversa selecionada/ }),
    ).toHaveAttribute('aria-current', 'page')
    fireEvent.click(screen.getByRole('button', { name: 'Renomear Prática de Python' }))
    fireEvent.click(screen.getByRole('button', { name: 'Excluir Prática de Python' }))
    expect(openRenameMock).toHaveBeenCalledWith('session-1')
    expect(openRemoveMock).toHaveBeenCalledWith('session-1')
    expect(
      within(rows[1]).getByRole('button', { name: 'Revisão de lógica' }),
    ).not.toHaveAttribute('aria-current')
    fireEvent.click(sessionRow.getByRole('button', { name: /conversa selecionada/ }))
    expect(selectSessionMock).toHaveBeenCalledWith('session-1')

    useSessionHistoryMock.mockReturnValue({
      ...historyState,
      isReadingHistory: true,
    })
    rerender(<SessionHistory />)
    expect(screen.getByRole('status')).toHaveTextContent('Carregando histórico…')
    expect(screen.getByRole('button', { name: 'Revisão de lógica' })).toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Renomear Prática de Python' }),
    ).toBeEnabled()
    // Decorative placeholders have no accessible role; inspect the shared primitive marker.
    const placeholders = document.querySelectorAll('[data-slot="skeleton"]')
    expect(placeholders).toHaveLength(12)
    for (const placeholder of placeholders) {
      expect(placeholder.closest('[aria-hidden="true"]')).not.toBeNull()
    }
  })

  it('shows the empty state, retries failures and pages when the list is ready', () => {
    const refresh = vi.fn()
    const loadMoreSessions = vi.fn()
    useSessionHistoryMock.mockReturnValue({
      historyError: 'Falha ao carregar',
      isReadingHistory: true,
      listRef: { current: null },
      loadMoreSessions,
      loadSentinelRef: { current: null },
      openRemoveDialog: openRemoveMock,
      openRenameDialog: openRenameMock,
      search: 'curso',
      selectSession: selectSessionMock,
      selectedSessionId: null,
      sessionsPage: { items: [], nextCursor: 'next' },
      setSearch: setSearchMock,
      refresh,
    } as unknown as ReturnType<typeof useSessionHistory>)
    const { rerender } = render(<SessionHistory />)
    expect(screen.getByRole('status')).toHaveTextContent('Carregando histórico…')
    expect(
      screen.queryByRole('button', { name: /Renomear|Excluir/ }),
    ).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Carregar mais conversas' })).toBeDisabled()
    expect(
      screen.queryByText('Suas conversas aceitas aparecerão aqui.'),
    ).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(refresh).toHaveBeenCalledOnce()

    useSessionHistoryMock.mockReturnValue({
      historyError: null,
      isReadingHistory: false,
      listRef: { current: null },
      loadMoreSessions,
      loadSentinelRef: { current: null },
      openRemoveDialog: openRemoveMock,
      openRenameDialog: openRenameMock,
      search: '',
      selectSession: selectSessionMock,
      selectedSessionId: null,
      sessionsPage: { items: [], nextCursor: 'next' },
      setSearch: setSearchMock,
      refresh,
    } as unknown as ReturnType<typeof useSessionHistory>)
    rerender(<SessionHistory />)
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
    expect(document.querySelectorAll('[data-slot="skeleton"]')).toHaveLength(0)
    expect(screen.getByText('Suas conversas aceitas aparecerão aqui.')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Carregar mais conversas' }))
    expect(loadMoreSessions).toHaveBeenCalledOnce()
  })
})
