import { vi } from 'vitest'

/** Deterministic browser ports; persistence behavior is asserted through page consumers. */
export function installDraftBrowserStorage() {
  const records = new Map<IDBValidKey, unknown>()
  const channels = new Set<BroadcastChannelMock>()
  type Failure = {
    mode: IDBTransactionMode | 'open'
    operation: 'get' | 'cursor' | 'open'
    event: 'request-error' | 'transaction-error' | 'abort'
  }
  let pendingFailure: Failure | null = null
  function takeFailure(mode: Failure['mode'], operation: Failure['operation']) {
    if (pendingFailure?.mode !== mode || pendingFailure.operation !== operation)
      return null
    const failure = pendingFailure
    pendingFailure = null
    return failure
  }
  class BroadcastChannelMock {
    onmessage: ((event: MessageEvent) => void) | null = null
    constructor(_name: string) {
      channels.add(this)
    }
    postMessage(data: unknown) {
      for (const channel of channels)
        if (channel !== this) channel.onmessage?.({ data } as MessageEvent)
    }
    close() {
      channels.delete(this)
    }
  }
  const database = {
    createObjectStore: vi.fn(),
    close: vi.fn(),
    transaction: vi.fn((_storeName: string, mode: IDBTransactionMode) => {
      const transaction = {
        error: new DOMException('Local draft storage failed', 'AbortError'),
        oncomplete: null as (() => void) | null,
        onerror: null as (() => void) | null,
        onabort: null as (() => void) | null,
        objectStore: () => ({
          get(key: IDBValidKey) {
            const failure = takeFailure(mode, 'get')
            const request = {
              result: undefined as unknown,
              error: new DOMException('Draft read failed', 'UnknownError'),
              onsuccess: null as (() => void) | null,
              onerror: null as (() => void) | null,
            }
            queueMicrotask(() => {
              if (failure) {
                if (failure.event === 'request-error') request.onerror?.()
                else if (failure.event === 'abort') transaction.onabort?.()
                else transaction.onerror?.()
                return
              }
              request.result = records.get(key)
              request.onsuccess?.()
              setTimeout(() => transaction.oncomplete?.(), 0)
            })
            return request
          },
          put(value: unknown, key: IDBValidKey) {
            records.set(key, structuredClone(value))
            return {}
          },
          openCursor() {
            const failure = takeFailure(mode, 'cursor')
            const entries = [...records.entries()]
            let index = 0
            const request = {
              result: null as null | {
                value: unknown
                delete: () => void
                update: (value: unknown) => void
                continue: () => void
              },
              onsuccess: null as (() => void) | null,
            }
            function next() {
              queueMicrotask(() => {
                const entry = entries[index++]
                request.result = entry
                  ? {
                      value: entry[1],
                      delete: () => {
                        records.delete(entry[0])
                      },
                      update: (value) => {
                        records.set(entry[0], structuredClone(value))
                      },
                      continue: next,
                    }
                  : null
                request.onsuccess?.()
                if (!entry) setTimeout(() => transaction.oncomplete?.(), 0)
              })
            }
            if (failure) {
              queueMicrotask(() => {
                if (failure.event === 'abort') transaction.onabort?.()
                else transaction.onerror?.()
              })
            } else next()
            return request
          },
        }),
      }
      return transaction
    }),
  }
  vi.stubGlobal('BroadcastChannel', BroadcastChannelMock)
  vi.stubGlobal('indexedDB', {
    open: vi.fn(() => {
      const failure = takeFailure('open', 'open')
      const request = {
        result: database,
        error: new DOMException('Draft database unavailable', 'UnknownError'),
        onsuccess: null as (() => void) | null,
        onerror: null as (() => void) | null,
        onupgradeneeded: null as (() => void) | null,
      }
      queueMicrotask(() => {
        if (failure) {
          request.onerror?.()
          return
        }
        request.onupgradeneeded?.()
        request.onsuccess?.()
      })
      return request
    }),
  })
  return {
    records,
    rejectNext(
      mode: Failure['mode'],
      operation: Failure['operation'],
      event: Failure['event'],
    ) {
      pendingFailure = { mode, operation, event }
    },
    publish(data: unknown) {
      for (const channel of channels) channel.onmessage?.({ data } as MessageEvent)
    },
  }
}
