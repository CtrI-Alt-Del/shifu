import {
  isValidReactQuestionDraft,
  nextReactQuestionDraftGeneration,
  type ReactQuestionDraft,
  type ReactQuestionDraftKey,
  type ReactQuestionDraftStore,
  type BrowserDataCapabilityClient,
  type BrowserDataCapabilityState,
} from '@/core/learning/react-question-draft/react-question-draft-store'

const DATABASE_NAME = 'shifu-react-question-drafts'
const STORE_NAME = 'drafts'
const CAPABILITY_STORE_NAME = 'account-capabilities'
const CHANNEL_NAME = 'shifu-react-question-drafts'
const MAX_SOURCE_BYTES = 256 * 1024
const TAB_ID = `${Date.now()}-${Math.random()}`
const VALIDATION_CACHE_MS = 15_000
const accountListeners = new Set<{
  accountId: string
  listener: (event: {
    generation: number
    tombstone: boolean
    accountRevoked?: boolean
  }) => void
}>()

type AccountCapabilityRecord = {
  accountId: string
  state: BrowserDataCapabilityState
  capability: string | null
}

function revocationMarkerKey(accountId: string) {
  return `shifu:account-data-revoked:${accountId}`
}

function hasRevocationMarker(accountId: string) {
  try {
    return globalThis.localStorage?.getItem(revocationMarkerKey(accountId)) === '1'
  } catch {
    return false
  }
}

function setRevocationMarker(accountId: string) {
  try {
    globalThis.localStorage?.setItem(revocationMarkerKey(accountId), '1')
  } catch {
    // The durable IndexedDB marker remains authoritative when localStorage is unavailable.
  }
}

function dispatchAccountRevoked(accountId: string) {
  for (const entry of accountListeners)
    if (entry.accountId === accountId)
      entry.listener({ generation: 0, tombstone: true, accountRevoked: true })
  if (typeof BroadcastChannel !== 'undefined') {
    const channel = new BroadcastChannel(CHANNEL_NAME)
    channel.postMessage({ accountId, accountRevoked: true, sender: TAB_ID })
    channel.close()
  }
  if (typeof window !== 'undefined')
    window.dispatchEvent(
      new CustomEvent('shifu:account-data-revoked', { detail: { accountId } }),
    )
}
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
    const request = indexedDB.open(DATABASE_NAME, 2)
    request.onupgradeneeded = () => {
      const database = request.result
      if (!database.objectStoreNames.contains(STORE_NAME))
        database.createObjectStore(STORE_NAME)
      if (!database.objectStoreNames.contains(CAPABILITY_STORE_NAME))
        database.createObjectStore(CAPABILITY_STORE_NAME, { keyPath: 'accountId' })
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

function readCapabilityRecord(database: IDBDatabase, accountId: string) {
  return new Promise<AccountCapabilityRecord | undefined>((resolve, reject) => {
    const transaction = database.transaction(CAPABILITY_STORE_NAME, 'readonly')
    const request = transaction.objectStore(CAPABILITY_STORE_NAME).get(accountId)
    request.onsuccess = () =>
      resolve(request.result as AccountCapabilityRecord | undefined)
    request.onerror = () => reject(request.error)
  })
}

function persistCapabilityRecord(record: AccountCapabilityRecord) {
  return openDatabase().then(async (database) => {
    try {
      await new Promise<void>((resolve, reject) => {
        const transaction = database.transaction(CAPABILITY_STORE_NAME, 'readwrite')
        transaction.objectStore(CAPABILITY_STORE_NAME).put(record)
        transaction.oncomplete = () => resolve()
        transaction.onerror = () => reject(transaction.error)
        transaction.onabort = () => reject(transaction.error)
      })
    } finally {
      database.close()
    }
  })
}

function withActiveAccountDrafts(
  database: IDBDatabase,
  accountId: string,
  update: (store: IDBObjectStore) => void,
) {
  return new Promise<boolean>((resolve, reject) => {
    const transaction = database.transaction(
      [STORE_NAME, CAPABILITY_STORE_NAME],
      'readwrite',
    )
    let active = false
    const request = transaction.objectStore(CAPABILITY_STORE_NAME).get(accountId)
    request.onsuccess = () => {
      const capability = request.result as AccountCapabilityRecord | undefined
      if (
        hasRevocationMarker(accountId) ||
        capability?.state !== 'active' ||
        !capability.capability
      )
        return
      active = true
      update(transaction.objectStore(STORE_NAME))
    }
    request.onerror = () => reject(request.error)
    transaction.oncomplete = () => resolve(active)
    transaction.onerror = () => reject(transaction.error)
    transaction.onabort = () => reject(transaction.error)
  })
}

export const IndexedDbReactQuestionDraftStore = (
  capabilityClient?: BrowserDataCapabilityClient,
): ReactQuestionDraftStore => {
  const validationByAccount = new Map<string, Promise<BrowserDataCapabilityState>>()
  const unavailableStorageByAccount = new Set<string>()
  const validatedAccountCapabilities = new Map<
    string,
    { state: BrowserDataCapabilityState; validatedAt: number }
  >()

  async function revokeAccount(accountId: string) {
    setRevocationMarker(accountId)
    const database = await openDatabase()
    try {
      await new Promise<void>((resolve, reject) => {
        const transaction = database.transaction(
          [STORE_NAME, CAPABILITY_STORE_NAME],
          'readwrite',
        )
        transaction.objectStore(CAPABILITY_STORE_NAME).put({
          accountId,
          state: 'revoked',
          capability: null,
        } satisfies AccountCapabilityRecord)
        const cursor = transaction.objectStore(STORE_NAME).openCursor()
        cursor.onsuccess = () => {
          const current = cursor.result
          if (!current) return
          const draft = current.value as Partial<ReactQuestionDraft>
          if (draft.accountId === accountId) current.delete()
          current.continue()
        }
        transaction.oncomplete = () => resolve()
        transaction.onerror = () => reject(transaction.error)
        transaction.onabort = () => reject(transaction.error)
      })
    } finally {
      database.close()
    }
    dispatchAccountRevoked(accountId)
    validatedAccountCapabilities.set(accountId, {
      state: 'revoked',
      validatedAt: Date.now(),
    })
  }

  async function validateAccountCapability(
    accountId: string,
    force = false,
  ): Promise<BrowserDataCapabilityState> {
    const cached = validatedAccountCapabilities.get(accountId)
    if (
      !force &&
      cached?.state === 'active' &&
      Date.now() - cached.validatedAt < VALIDATION_CACHE_MS
    )
      return 'active'
    const existing = validationByAccount.get(accountId)
    if (existing) return existing
    const validation = validateAccountCapabilityForStore(accountId)
    validationByAccount.set(accountId, validation)
    try {
      return await validation
    } finally {
      validationByAccount.delete(accountId)
    }
  }

  async function validateAccountCapabilityForStore(
    accountId: string,
  ): Promise<BrowserDataCapabilityState> {
    if (hasRevocationMarker(accountId)) {
      await revokeAccount(accountId)
      return 'revoked'
    }
    if (!capabilityClient)
      throw new Error('Browser data capability client is unavailable')
    if (typeof navigator !== 'undefined' && !navigator.onLine)
      throw new Error('Browser data capability cannot be checked offline')

    let existing: AccountCapabilityRecord | undefined
    let database: IDBDatabase | undefined
    let storageUnavailable = false
    try {
      database = await openDatabase()
      existing = await readCapabilityRecord(database, accountId)
    } catch {
      storageUnavailable = true
    } finally {
      database?.close()
    }
    if (existing?.state === 'revoked') {
      await revokeAccount(accountId)
      return 'revoked'
    }

    const capability =
      existing?.state === 'active' && existing.capability
        ? existing.capability
        : await capabilityClient.issueBrowserDataCapability()
    if (!capability) throw new Error('Browser data capability is unavailable')
    const state = await capabilityClient.validateBrowserDataCapability(capability)
    if (state === 'revoked') {
      await revokeAccount(accountId)
      return 'revoked'
    }
    if (!storageUnavailable) {
      try {
        await persistCapabilityRecord({ accountId, state: 'active', capability })
      } catch {
        storageUnavailable = true
      }
    }
    if (storageUnavailable) unavailableStorageByAccount.add(accountId)
    else unavailableStorageByAccount.delete(accountId)
    validatedAccountCapabilities.set(accountId, {
      state: 'active',
      validatedAt: Date.now(),
    })
    return 'active'
  }

  const draftStore: ReactQuestionDraftStore = {
    validateAccountCapability,
    revokeAccount,

    async read(key: ReactQuestionDraftKey): Promise<ReactQuestionDraft | null> {
      if (unavailableStorageByAccount.delete(key.accountId))
        throw new Error('Local browser draft storage is unavailable')
      if ((await validateAccountCapability(key.accountId)) === 'revoked') return null
      const database = await openDatabase()
      try {
        const value = await new Promise<unknown>((resolve, reject) => {
          const transaction = database.transaction(
            [STORE_NAME, CAPABILITY_STORE_NAME],
            'readonly',
          )
          const capabilityRequest = transaction
            .objectStore(CAPABILITY_STORE_NAME)
            .get(key.accountId)
          let draft: unknown = null
          capabilityRequest.onsuccess = () => {
            const capability = capabilityRequest.result as
              | AccountCapabilityRecord
              | undefined
            if (
              hasRevocationMarker(key.accountId) ||
              capability?.state !== 'active' ||
              !capability.capability
            )
              return
            const request = transaction.objectStore(STORE_NAME).get(keyOf(key))
            request.onsuccess = () => {
              draft = request.result ?? null
            }
            request.onerror = () => reject(request.error)
          }
          capabilityRequest.onerror = () => reject(capabilityRequest.error)
          transaction.oncomplete = () =>
            resolve(hasRevocationMarker(key.accountId) ? null : draft)
          transaction.onerror = () => reject(transaction.error)
          transaction.onabort = () => reject(transaction.error)
        })
        if (value === null || value === undefined) return null
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
          const transaction = database.transaction(
            [STORE_NAME, CAPABILITY_STORE_NAME],
            'readwrite',
          )
          const store = transaction.objectStore(STORE_NAME)
          const id = keyOf(key)
          let generation = 0
          const capabilityRequest = transaction
            .objectStore(CAPABILITY_STORE_NAME)
            .get(key.accountId)
          capabilityRequest.onsuccess = () => {
            const capability = capabilityRequest.result as
              | AccountCapabilityRecord
              | undefined
            if (
              hasRevocationMarker(key.accountId) ||
              capability?.state !== 'active' ||
              !capability.capability
            )
              return
            const request = store.get(id)
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
            request.onerror = () => reject(request.error)
          }
          capabilityRequest.onerror = () => reject(capabilityRequest.error)
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
        let generation = 0
        await withActiveAccountDrafts(database, key.accountId, (store) => {
          const id = keyOf(key)
          const request = store.get(id)
          request.onsuccess = () => {
            generation = nextReactQuestionDraftGeneration(
              (request.result as { generation?: unknown } | undefined)?.generation,
            )
            store.put(
              {
                ...key,
                schemaVersion: 1,
                files: [],
                generation,
                savedAt: Date.now(),
                tombstone: true,
              } satisfies ReactQuestionDraft,
              id,
            )
          }
        })
        if (generation > 0) notifyDraftChange(key, generation, true)
        return generation
      } finally {
        database.close()
      }
    },

    async tombstoneActivity(accountId: string, activityId: string) {
      if ((await validateAccountCapability(accountId)) !== 'active') return
      const database = await openDatabase()
      try {
        const tombstones: ReactQuestionDraft[] = []
        await withActiveAccountDrafts(database, accountId, (store) => {
          const cursor = store.openCursor()
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
              tombstones.push(tombstone)
            }
            current.continue()
          }
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
      if ((await validateAccountCapability(key.accountId)) !== 'active') return
      const database = await openDatabase()
      try {
        const tombstones: ReactQuestionDraft[] = []
        await withActiveAccountDrafts(database, key.accountId, (store) => {
          const cursor = store.openCursor()
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
              tombstones.push(tombstone)
            }
            current.continue()
          }
        })
        for (const draft of tombstones) notifyDraftChange(draft, draft.generation, true)
      } finally {
        database.close()
      }
    },

    subscribe(
      key: ReactQuestionDraftKey,
      listener: (event: {
        generation: number
        tombstone: boolean
        accountRevoked?: boolean
      }) => void,
    ) {
      const entry = { accountId: key.accountId, listener }
      accountListeners.add(entry)
      const channel =
        typeof BroadcastChannel === 'undefined'
          ? null
          : new BroadcastChannel(CHANNEL_NAME)
      if (channel)
        channel.onmessage = (
          event: MessageEvent<{
            key?: string
            accountId?: string
            accountRevoked?: boolean
            generation?: number
            tombstone?: boolean
            sender?: string
          }>,
        ) => {
          if (event.data?.sender === TAB_ID) return
          if (
            event.data?.accountRevoked === true &&
            event.data.accountId === key.accountId
          ) {
            listener({ generation: 0, tombstone: true, accountRevoked: true })
            return
          }
          if (
            event.data?.key === keyOf(key) &&
            typeof event.data.generation === 'number' &&
            typeof event.data.tombstone === 'boolean'
          )
            listener({
              generation: event.data.generation,
              tombstone: event.data.tombstone,
            })
        }
      const onStorage = (event: StorageEvent) => {
        if (event.key === revocationMarkerKey(key.accountId) && event.newValue === '1')
          void revokeAccount(key.accountId).catch(() => undefined)
      }
      if (typeof window !== 'undefined') window.addEventListener('storage', onStorage)
      if (hasRevocationMarker(key.accountId))
        void revokeAccount(key.accountId).catch(() => undefined)
      return () => {
        accountListeners.delete(entry)
        channel?.close()
        if (typeof window !== 'undefined')
          window.removeEventListener('storage', onStorage)
      }
    },

    async clearTombstone(
      key: ReactQuestionDraftKey,
      files: readonly { path: string; content: string }[],
      expectedGeneration: number,
    ) {
      const database = await openDatabase()
      try {
        let generation = 0
        await withActiveAccountDrafts(database, key.accountId, (store) => {
          const id = keyOf(key)
          const request = store.get(id)
          request.onsuccess = () => {
            const previous = request.result as ReactQuestionDraft | undefined
            if (!previous?.tombstone || previous.generation !== expectedGeneration) return
            generation = (previous?.generation ?? 0) + 1
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
        })
        if (generation > 0) notifyDraftChange(key, generation, false)
        return generation
      } finally {
        database.close()
      }
    },
  }

  return draftStore
}
