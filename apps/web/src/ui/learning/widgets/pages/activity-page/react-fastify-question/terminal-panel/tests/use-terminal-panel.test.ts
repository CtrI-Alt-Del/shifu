import { act, cleanup, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useTerminalPanel, type TerminalPanelProps } from '../use-terminal-panel'
function props(): TerminalPanelProps {
  return {
    transcript: 'Pronto',
    commands: [{ id: 'api', executable: 'npm', arguments: ['run', 'dev:api'] }],
    onRunCommand: vi.fn(async () => undefined),
  }
}
describe('useTerminalPanel', () => {
  afterEach(cleanup)
  it.each([
    'npm install',
    'npm run dev:api; id',
    'npm run dev:api | cat',
    'npm run dev:api --extra',
    '$(id)',
    ' npm run dev:api',
  ])('rejects unauthorized command %s', async (command) => {
    const current = props()
    const { result } = renderHook(() => useTerminalPanel(current))
    act(() => result.current.handleCommandChange(command))
    await act(() => result.current.handleRun())
    expect(result.current.error).toContain('Comando não permitido')
    expect(current.onRunCommand).not.toHaveBeenCalled()
  })
  it('dispatches only the matching curricular command ID and recovers from failure', async () => {
    const current = props()
    vi.mocked(current.onRunCommand).mockRejectedValueOnce(new Error('unavailable'))
    const { result } = renderHook(() => useTerminalPanel(current))
    act(() => result.current.handleCommandChange('npm run dev:api'))
    await act(() => result.current.handleRun())
    expect(result.current.error).toContain('Não foi possível')
    expect(current.onRunCommand).toHaveBeenCalledWith('api')
    await act(() => result.current.handleRun())
    expect(result.current.error).toBeNull()
    expect(result.current.isRunning).toBe(false)
  })
})
