import { act, cleanup, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useHttpPanel, type HttpPanelProps } from '../use-http-panel'
const EXAMPLES: HttpPanelProps['examples'] = [
  { key: 'list', title: 'Listar tarefas', method: 'GET', path: '/api/tasks', body: null },
  {
    key: 'complete',
    title: 'Concluir tarefa',
    method: 'PATCH',
    path: '/api/tasks/1',
    body: '{"done":true}',
  },
]
function props(): HttpPanelProps {
  return {
    examples: EXAMPLES,
    isReady: true,
    onRequest: vi.fn(async () => ({
      status: 200,
      headers: [],
      body: '[]',
      truncated: false,
    })),
  }
}
describe('useHttpPanel', () => {
  afterEach(cleanup)
  it('fills examples without sending and excludes a GET body', async () => {
    const current = props()
    const { result, rerender } = renderHook(useHttpPanel, { initialProps: current })
    expect(result.current.method).toBe('GET')
    expect(result.current.hasBody).toBe(false)
    act(() =>
      result.current.handleExample(
        EXAMPLES[1] ??
          EXAMPLES[0] ?? {
            key: 'missing',
            title: 'missing',
            method: 'GET',
            path: '/api',
            body: null,
          },
      ),
    )
    expect(result.current.path).toBe('/api/tasks/1')
    expect(result.current.hasBody).toBe(true)
    rerender({ ...current, examples: [...EXAMPLES] })
    expect(current.onRequest).not.toHaveBeenCalled()
    await act(() => result.current.handleSend())
    expect(current.onRequest).toHaveBeenCalledWith(
      { method: 'PATCH', path: '/api/tasks/1', body: '{"done":true}' },
      expect.any(AbortSignal),
    )
    expect(result.current.response?.status).toBe(200)
    act(() => {
      result.current.handleMethodChange('GET')
      result.current.handlePathChange('/api/tasks')
      result.current.handleBodyChange('ignored')
    })
    await act(() => result.current.handleSend())
    expect(current.onRequest).toHaveBeenLastCalledWith(
      { method: 'GET', path: '/api/tasks' },
      expect.any(AbortSignal),
    )
  })
  it('keeps an old cancelled response from overwriting the latest request', async () => {
    const current = props()
    let finish:
      | ((value: Awaited<ReturnType<HttpPanelProps['onRequest']>>) => void)
      | undefined
    vi.mocked(current.onRequest).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          finish = resolve
        }),
    )
    const { result } = renderHook(() => useHttpPanel(current))
    let pending: Promise<void> = Promise.resolve()
    act(() => {
      pending = result.current.handleSend()
    })
    expect(result.current.isSending).toBe(true)
    act(() => result.current.handleCancel())
    expect(result.current.error).toBe('Requisição cancelada.')
    await act(() => result.current.handleSend())
    await act(async () => {
      finish?.({ status: 500, body: 'old', headers: [], truncated: false })
      await pending
    })
    expect(result.current.response?.status).toBe(200)
    expect(result.current.isSending).toBe(false)
  })
  it('blocks unavailable API requests and exposes recoverable transport errors', async () => {
    const current = props()
    const { result, rerender } = renderHook(useHttpPanel, {
      initialProps: { ...current, isReady: false },
    })
    await act(() => result.current.handleSend())
    expect(current.onRequest).not.toHaveBeenCalled()
    rerender(current)
    vi.mocked(current.onRequest).mockRejectedValueOnce(new Error('offline'))
    await act(() => result.current.handleSend())
    expect(result.current.error).toContain('Não foi possível')
    await act(() => result.current.handleSend())
    expect(result.current.error).toBeNull()
    expect(result.current.response?.body).toBe('[]')
  })
  it('aborts an outstanding request on unmount', () => {
    const current = props()
    vi.mocked(current.onRequest).mockImplementation(() => new Promise(() => {}))
    const { result, unmount } = renderHook(() => useHttpPanel(current))
    act(() => {
      void result.current.handleSend()
    })
    const signal = vi.mocked(current.onRequest).mock.calls[0]?.[1]
    unmount()
    expect(signal?.aborted).toBe(true)
  })
})
