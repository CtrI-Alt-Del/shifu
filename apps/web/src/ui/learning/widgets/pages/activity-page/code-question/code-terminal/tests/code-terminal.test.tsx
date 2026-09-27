import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { CodeTerminal } from '..'
import { useCodeTerminal } from '../use-code-terminal'

vi.mock('../use-code-terminal', () => ({ useCodeTerminal: vi.fn() }))
const useCodeTerminalMock = vi.mocked(useCodeTerminal)

describe('CodeTerminal', () => {
  afterEach(cleanup)
  beforeEach(() =>
    useCodeTerminalMock.mockReturnValue({
      status: 'ready',
      statusText: 'Prática pronta',
      terminalElementRef: { current: null },
      transcript: '2\n',
    }),
  )

  it('shows the interactive terminal and transcript without duplicate input controls', () => {
    render(<CodeTerminal runner={null} />)
    expect(screen.getByRole('application', { name: /Terminal interativo/ })).toBeVisible()
    expect(
      screen.getByRole('log', { name: 'Transcrição do Terminal' }),
    ).toHaveTextContent('2')
    expect(screen.getByText('Prática pronta')).toBeVisible()
    expect(
      screen.queryByRole('button', { name: /Enviar entrada|Enviar comando/ }),
    ).not.toBeInTheDocument()
  })

  it('shows unavailable practice in the transcript', () => {
    useCodeTerminalMock.mockReturnValue({
      status: 'unavailable',
      statusText: 'Prática indisponível',
      terminalElementRef: { current: null },
      transcript: '',
    })
    render(<CodeTerminal runner={null} />)
    expect(
      screen.getByRole('log', { name: 'Transcrição do Terminal' }),
    ).toHaveTextContent('A prática está indisponível')
  })

  it('keeps the terminal header clear while the practice waits for input', () => {
    useCodeTerminalMock.mockReturnValue({
      status: 'waiting-input',
      statusText: 'Aguardando entrada padrão',
      terminalElementRef: { current: null },
      transcript: '',
    })
    render(<CodeTerminal runner={null} />)
    expect(screen.queryByText('Aguardando entrada padrão')).not.toBeInTheDocument()
  })
})
