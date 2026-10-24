import {
  isValidReactQuestionDraft,
  nextReactQuestionDraftGeneration,
  type ReactQuestionDraft,
  type ReactQuestionDraftKey,
  type ReactQuestionDraftStore,
} from '@/core/learning/react-question-draft/react-question-draft-store'

const DATABASE_NAME = 'shifu-react-question-drafts'
const STORE_NAME = 'drafts'
const CHANNEL_NAME = 'shifu-react-question-drafts'
const MAX_SOURCE_BYTES = 256 * 1024
const TAB_ID = `${Date.now()}-${Math.random()}`
function keyOf(key: ReactQuestionDraftKey) {
  return [
    key.accountId,
    key.goalId,
    key.skillId,
    key.competencyId,
    key.activityId,
    key.questionKey,
    key.activityRevision,
  ].join('\u001f')
}

function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DATABASE_NAME, 1)
    request.onupgradeneeded = () => {
      request.result.createObjectStore(STORE_NAME)
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

function sourceSize(files: readonly { path: string; content: string }[]) {
  return files.reduce(
    (total, file) => total + new TextEncoder().encode(file.content).byteLength,
    0,
  )
}

function notifyDraftChange(
  key: ReactQuestionDraftKey,
  generation: number,
  tombstone: boolean,
) {
  if (typeof BroadcastChannel === 'undefined') return
  const channel = new BroadcastChannel(CHANNEL_NAME)
  channel.postMessage({
    key: keyOf(key),
    accountId: key.accountId,
    generation,
    tombstone,
    sender: TAB_ID,
  })
  channel.close()
}

export const IndexedDbReactQuestionDraftStore = (): ReactQuestionDraftStore => {
  const draftStore: ReactQuestionDraftStore = {
    async read(key: ReactQuestionDraftKey): Promise<ReactQuestionDraft | null> {
      const database = await openDatabase()
      try {
        const value = await new Promise<unknown>((resolve, reject) => {
          const transaction = database.transaction(STORE_NAME, 'readonly')
          const request = transaction.objectStore(STORE_NAME).get(keyOf(key))
          request.onsuccess = () => resolve(request.result)
          request.onerror = () => reject(request.error)
        })
        if (value === undefined) return null
        if (isValidReactQuestionDraft(value, key)) return value
      } finally {
        database.close()
      }
      const generation = await draftStore.tombstone(key)
      return {
        ...key,
        schemaVersion: 1,
        files: [],
        generation,
        savedAt: Date.now(),
        tombstone: true,
      }
    },

    async write(
      key: ReactQuestionDraftKey,
      files: readonly { path: string; content: string }[],
      expectedGeneration: number,
    ) {
      if (sourceSize(files) > MAX_SOURCE_BYTES) return 0
      const database = await openDatabase()
      try {
        const generation = await new Promise<number>((resolve, reject) => {
          const transaction = database.transaction(STORE_NAME, 'readwrite')
          const store = transaction.objectStore(STORE_NAME)
          const id = keyOf(key)
          const request = store.get(id)
          let generation = 0
          request.onsuccess = () => {
            const existing = request.result as ReactQuestionDraft | undefined
            if (
              existing?.tombstone ||
              (existing?.generation ?? 0) !== expectedGeneration
            ) {
              generation = 0
              return
            }
            generation = (existing?.generation ?? 0) + 1
            store.put(
              {
                ...key,
                schemaVersion: 1,
                files: files.map((file) => ({ ...file })),
                generation,
                savedAt: Date.now(),
                tombstone: false,
              } satisfies ReactQuestionDraft,
              id,
            )
          }
          transaction.oncomplete = () => resolve(generation)
          transaction.onerror = () => reject(transaction.error)
          transaction.onabort = () => reject(transaction.error)
        })
        if (generation > 0) notifyDraftChange(key, generation, false)
        return generation
      } finally {
        database.close()
      }
    },

    async tombstone(key: ReactQuestionDraftKey) {
      const database = await openDatabase()
      try {
        const generation = await new Promise<number>((resolve, reject) => {
          const transaction = database.transaction(STORE_NAME, 'readwrite')
          const store = transaction.objectStore(STORE_NAME)
          const id = keyOf(key)
          const request = store.get(id)
          let nextGeneration = 1
          request.onsuccess = () => {
            nextGeneration = nextReactQuestionDraftGeneration(
              (request.result as { generation?: unknown } | undefined)?.generation,
            )
            store.put(
              {
                ...key,
                schemaVersion: 1,
                files: [],
                generation: nextGeneration,
                savedAt: Date.now(),
                tombstone: true,
              } satisfies ReactQuestionDraft,
              id,
            )
          }
          transaction.oncomplete = () => resolve(nextGeneration)
          transaction.onerror = () => reject(transaction.error)
          transaction.onabort = () => reject(transaction.error)
        })
        notifyDraftChange(key, generation, true)
        return generation
      } finally {
        database.close()
      }
    },

    async tombstoneActivity(accountId: string, activityId: string) {
      const database = await openDatabase()
      try {
        const tombstones = await new Promise<ReactQuestionDraft[]>((resolve, reject) => {
          const transaction = database.transaction(STORE_NAME, 'readwrite')
          const store = transaction.objectStore(STORE_NAME)
          const cursor = store.openCursor()
          const removed: ReactQuestionDraft[] = []
          cursor.onsuccess = () => {
            const current = cursor.result
            if (!current) return
            const draft = current.value as ReactQuestionDraft
            if (draft.accountId === accountId && draft.activityId === activityId) {
              const tombstone = {
                ...draft,
                files: [],
                generation: nextReactQuestionDraftGeneration(draft.generation),
                savedAt: Date.now(),
                tombstone: true,
              }
              current.update(tombstone)
              removed.push(tombstone)
            }
            current.continue()
          }
          transaction.oncomplete = () => resolve(removed)
          transaction.onerror = () => reject(transaction.error)
          transaction.onabort = () => reject(transaction.error)
        })
        for (const draft of tombstones) notifyDraftChange(draft, draft.generation, true)
      } finally {
        database.close()
      }
    },

    async tombstoneStaleActivity(
      key: Pick<
        ReactQuestionDraftKey,
        'accountId' | 'goalId' | 'skillId' | 'competencyId' | 'activityId'
      >,
      activityRevision: string,
      activeQuestionKeys: readonly string[],
    ) {
      const database = await openDatabase()
      try {
        const tombstones = await new Promise<ReactQuestionDraft[]>((resolve, reject) => {
          const transaction = database.transaction(STORE_NAME, 'readwrite')
          const store = transaction.objectStore(STORE_NAME)
          const cursor = store.openCursor()
          const removed: ReactQuestionDraft[] = []
          cursor.onsuccess = () => {
            const current = cursor.result
            if (!current) return
            const draft = current.value as ReactQuestionDraft
            const isSameActivity =
              draft.accountId === key.accountId &&
              draft.goalId === key.goalId &&
              draft.skillId === key.skillId &&
              draft.competencyId === key.competencyId &&
              draft.activityId === key.activityId
            if (
              isSameActivity &&
              !draft.tombstone &&
              (draft.activityRevision !== activityRevision ||
                !activeQuestionKeys.includes(draft.questionKey))
            ) {
              const tombstone = {
                ...draft,
                files: [],
                generation: nextReactQuestionDraftGeneration(draft.generation),
                savedAt: Date.now(),
                tombstone: true,
              }
              current.update(tombstone)
              removed.push(tombstone)
            }
            current.continue()
          }
          transaction.oncomplete = () => resolve(removed)
          transaction.onerror = () => reject(transaction.error)
          transaction.onabort = () => reject(transaction.error)
        })
        for (const draft of tombstones) notifyDraftChange(draft, draft.generation, true)
      } finally {
        database.close()
      }
    },

    subscribe(
      key: ReactQuestionDraftKey,
      listener: (event: { generation: number; tombstone: boolean }) => void,
    ) {
      if (typeof BroadcastChannel === 'undefined') return () => undefined
      const channel = new BroadcastChannel(CHANNEL_NAME)
      channel.onmessage = (
        event: MessageEvent<{
          key?: string
          generation?: number
          tombstone?: boolean
          sender?: string
        }>,
      ) => {
        if (
          event.data?.sender !== TAB_ID &&
          event.data?.key === keyOf(key) &&
          typeof event.data.generation === 'number' &&
          typeof event.data.tombstone === 'boolean'
        )
          listener({ generation: event.data.generation, tombstone: event.data.tombstone })
      }
      return () => channel.close()
    },

    async clearTombstone(
      key: ReactQuestionDraftKey,
      files: readonly { path: string; content: string }[],
      expectedGeneration: number,
    ) {
      const database = await openDatabase()
      try {
        const generation = await new Promise<number>((resolve, reject) => {
          const transaction = database.transaction(STORE_NAME, 'readwrite')
          const store = transaction.objectStore(STORE_NAME)
          const id = keyOf(key)
          const request = store.get(id)
          let nextGeneration = 1
          request.onsuccess = () => {
            const previous = request.result as ReactQuestionDraft | undefined
            if (!previous?.tombstone || previous.generation !== expectedGeneration) {
              nextGeneration = 0
              return
            }
            nextGeneration = (previous?.generation ?? 0) + 1
            store.put(
              {
                ...key,
                schemaVersion: 1,
                files: files.map((file) => ({ ...file })),
                generation: nextGeneration,
                savedAt: Date.now(),
                tombstone: false,
              } satisfies ReactQuestionDraft,
              id,
            )
          }
          transaction.oncomplete = () => resolve(nextGeneration)
          transaction.onerror = () => reject(transaction.error)
          transaction.onabort = () => reject(transaction.error)
        })
        notifyDraftChange(key, generation, false)
        return generation
      } finally {
        database.close()
      }
    },
  }

  return draftStore
}
