import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement, type ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { buildPracticePhotoPath, learningActivityPath } from '@/constants/routes'
import type { PracticalPreparationQuestion as PracticalPreparationQuestionData } from '@/core/learning/choice-activity'
import { RestResponse } from '@/core/shared/responses/rest-response'

import {
  type PracticalPreparationQuestionProps,
  usePracticalPreparationQuestion,
} from '../use-practical-preparation-question'

const mocks = vi.hoisted(() => ({
  getCurrentAccess: vi.fn(),
  get: vi.fn(),
  put: vi.fn(),
  delete: vi.fn(),
}))
vi.mock('@tanstack/react-start', () => ({
  createStart: () => ({}),
  createCsrfMiddleware: () => ({}),
  createMiddleware: () => ({ server: (handler: unknown) => handler }),
  createServerFn: () => ({
    middleware: () => ({
      validator: (validate: (data: unknown) => unknown) => ({
        handler:
          (handler: (context: { data: unknown }) => Promise<unknown>) =>
          (context: { data: unknown }) =>
            handler({
              data: validate(context.data),
              context: { requestId: 'test-request-id' },
            } as never),
      }),
    }),
  }),
}))
vi.mock('@tanstack/react-start/server', () => ({
  getRequest: () => new Request('http://shifu.test'),
}))
vi.mock('@/provision/auth/better-auth/better-auth-provider', () => ({
  getBetterAuthProvider: () => ({ getCurrentAccess: mocks.getCurrentAccess }),
}))
vi.mock('@/provision/auth/better-auth/better-auth-config', () => ({
  BetterAuthConfig: () => ({ identityURL: 'http://shifu.test' }),
}))
vi.mock('@/rest/axios/axios-rest-client', () => ({
  AxiosRestClient: () => ({
    get: mocks.get,
    put: mocks.put,
    delete: mocks.delete,
  }),
}))

const IDS = {
  goalId: '01J00000000000000000000001',
  skillId: '01J00000000000000000000002',
  competencyId: '01J00000000000000000000003',
  activityId: '01J00000000000000000000004',
}
const DRAFT_PATH = `${learningActivityPath(IDS)}/practice-draft`
const QUESTION: PracticalPreparationQuestionData = {
  key: 'practice-1',
  kind: 'practical_preparation',
  prompt: 'Prepare legumes salteados.',
  guidance: [],
  references: [],
  difficulty: 'easy',
  records: [
    { key: 'cuts', label: 'Cortes', mustShow: 'Os cortes' },
    { key: 'dish', label: 'Prato final', mustShow: 'O prato' },
  ],
  criteria: [],
}

function draftWire(
  revision: number,
  reflection: string | null,
  photos: readonly string[] = [],
) {
  return {
    revision,
    reflection,
    photos: photos.map((recordKey) => ({
      record_key: recordKey,
      photo_id: `photo-${recordKey}`,
      state: 'ready',
      media_type: 'image/jpeg',
      size_bytes: 1200,
    })),
  }
}

const onDraftStateChangeMock = vi.fn()
const onSessionExpiredMock = vi.fn()
const fetchMock = vi.fn()

function setup(props: Partial<PracticalPreparationQuestionProps> = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const view = renderHook(
    () =>
      usePracticalPreparationQuestion({
        question: QUESTION,
        questionNumber: 1,
        totalQuestions: 1,
        ids: IDS,
        isOnlineAuthority: true,
        onDraftStateChange: onDraftStateChangeMock,
        onSessionExpired: onSessionExpiredMock,
        ...props,
      }),
    {
      wrapper: ({ children }: { children: ReactNode }) =>
        createElement(QueryClientProvider, { client }, children),
    },
  )
  return { ...view, client }
}

function createFile(name = 'cortes.jpg') {
  return new File(['bytes'], name, { type: 'image/jpeg' })
}

describe('usePracticalPreparationQuestion through the REST service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.stubGlobal('fetch', fetchMock)
    mocks.getCurrentAccess.mockResolvedValue({
      accountId: 'account-1',
      accessToken: 'test-token',
    })
    mocks.get.mockResolvedValue(
      new RestResponse({
        statusCode: 200,
        body: draftWire(3, 'Usei fogo alto.', ['cuts']),
      }),
    )
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('restores the saved draft only after the session check and maps its wire fields', async () => {
    const { result } = setup()
    await waitFor(() => expect(result.current.viewState).toBe('ready'))

    expect(mocks.get).toHaveBeenCalledWith(DRAFT_PATH, {
      headers: { Authorization: 'Bearer test-token' },
    })
    expect(result.current.reflection).toBe('Usei fogo alto.')
    expect(result.current.records.map(({ status }) => status)).toEqual([
      'ready',
      'missing',
    ])
    expect(onDraftStateChangeMock).toHaveBeenLastCalledWith({
      revision: 3,
      reflection: 'Usei fogo alto.',
      isComplete: false,
      hasUnsavedChanges: false,
    })
  })

  it('does not request the draft while online authority is missing', () => {
    const { result } = setup({ isOnlineAuthority: false })

    expect(result.current.viewState).toBe('offline')
    expect(mocks.get).not.toHaveBeenCalled()
  })

  it('does not request the draft for malformed route identifiers', async () => {
    const { result } = setup({ ids: { ...IDS, activityId: 'invalid' } })

    await waitFor(() => expect(result.current.viewState).toBe('error'))

    expect(mocks.get).not.toHaveBeenCalled()
  })

  it('reports a rejected session when the draft read is unauthorized', async () => {
    mocks.get.mockResolvedValue(new RestResponse({ statusCode: 401 }))
    setup()

    await waitFor(() => expect(onSessionExpiredMock).toHaveBeenCalledTimes(1))
  })

  it('shows a recoverable error when the draft cannot be read', async () => {
    mocks.get.mockResolvedValue(new RestResponse({ statusCode: 503 }))
    const { result } = setup()

    await waitFor(() => expect(result.current.viewState).toBe('error'))
    mocks.get.mockResolvedValue(
      new RestResponse({ statusCode: 200, body: draftWire(1, null) }),
    )
    await act(async () => result.current.handleReloadDraft())

    await waitFor(() => expect(result.current.viewState).toBe('ready'))
    expect(result.current.reflection).toBe('')
  })

  it('saves the reflection through PUT and exposes the saved revision', async () => {
    mocks.put.mockResolvedValue(
      new RestResponse({ statusCode: 200, body: draftWire(4, 'Novo texto', ['cuts']) }),
    )
    const { result } = setup()
    await waitFor(() => expect(result.current.viewState).toBe('ready'))

    act(() => result.current.handleChangeReflection('Novo texto'))
    await act(async () => result.current.handleBlurReflection())

    await waitFor(() => expect(result.current.saveState).toBe('saved'))
    expect(mocks.put).toHaveBeenCalledWith(
      `${DRAFT_PATH}/reflection`,
      { reflection: 'Novo texto' },
      { headers: { Authorization: 'Bearer test-token' } },
    )
    expect(onDraftStateChangeMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ revision: 4, hasUnsavedChanges: false }),
    )
  })

  it('shows Não salvo when the reflection request fails and keeps the text', async () => {
    mocks.put.mockResolvedValue(new RestResponse({ statusCode: 503 }))
    const { result } = setup()
    await waitFor(() => expect(result.current.viewState).toBe('ready'))

    act(() => result.current.handleChangeReflection('Texto novo'))
    await act(async () => result.current.handleBlurReflection())

    await waitFor(() => expect(result.current.saveStateLabel).toBe('Rascunho não salvo'))
    expect(result.current.reflection).toBe('Texto novo')
  })

  it('removes a photo through DELETE and shows the record as missing', async () => {
    mocks.delete.mockResolvedValue(
      new RestResponse({ statusCode: 200, body: draftWire(4, 'Usei fogo alto.') }),
    )
    const { result } = setup()
    await waitFor(() => expect(result.current.viewState).toBe('ready'))

    await act(async () => result.current.handleRemovePhoto('cuts'))

    expect(mocks.delete).toHaveBeenCalledWith(`${DRAFT_PATH}/photos/cuts`, undefined, {
      headers: { Authorization: 'Bearer test-token' },
    })
    await waitFor(() => expect(result.current.records[0]?.status).toBe('missing'))
  })

  it('sends the photo through the same-origin BFF route with a UUID upload key', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ ...camelDraft(5, ['cuts', 'dish']) }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    const { result } = setup()
    await waitFor(() => expect(result.current.viewState).toBe('ready'))
    const file = createFile()

    await act(async () => result.current.handleSelectPhoto('dish', file))

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe(buildPracticePhotoPath({ ...IDS, recordKey: 'dish' }))
    expect(init.method).toBe('PUT')
    expect(init.credentials).toBe('same-origin')
    const body = init.body as FormData
    expect(body.get('file')).toBeInstanceOf(File)
    expect(body.get('upload_key')).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
    )
    await waitFor(() => expect(result.current.records[1]?.status).toBe('ready'))
    expect(result.current.records[1]?.thumbnailUrl).toBe(
      `${buildPracticePhotoPath({ ...IDS, recordKey: 'dish' })}?v=photo-dish`,
    )
    expect(onDraftStateChangeMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ revision: 5, isComplete: true }),
    )
  })

  it.each([
    [413, 'A foto excede 10 MB. Escolha uma foto menor.', false, undefined],
    [422, 'Este arquivo não é uma foto JPEG, PNG ou WebP válida.', false, undefined],
    [
      409,
      'Este rascunho foi encerrado. Recarregue a página.',
      false,
      'practice_draft_closed',
    ],
    [409, 'Há uma avaliação pendente nesta Habilidade.', false, 'conflict'],
    [
      409,
      'Não foi possível reutilizar este envio. Tente novamente.',
      true,
      'upload_key_conflict',
    ],
    [409, 'Não foi possível enviar a foto. Tente novamente.', true, undefined],
    [503, 'Não foi possível enviar a foto. Tente novamente.', true, undefined],
  ])(
    'maps a %s upload failure to its message and retry rule',
    async (status, message, canRetry, code) => {
      fetchMock.mockResolvedValue(
        new Response(JSON.stringify(code ? { code } : {}), { status }),
      )
      const { result } = setup()
      await waitFor(() => expect(result.current.viewState).toBe('ready'))

      await act(async () => result.current.handleSelectPhoto('dish', createFile()))

      expect(result.current.records[1]).toMatchObject({
        status: 'failed',
        message,
        canRetry,
      })
    },
  )

  it('expires the session when the BFF answers 401 to an upload', async () => {
    fetchMock.mockResolvedValue(new Response('{}', { status: 401 }))
    const { result } = setup()
    await waitFor(() => expect(result.current.viewState).toBe('ready'))

    await act(async () => result.current.handleSelectPhoto('dish', createFile()))

    expect(onSessionExpiredMock).toHaveBeenCalledTimes(1)
  })

  it('keeps a retryable failure when the network request itself fails', async () => {
    fetchMock.mockRejectedValue(new TypeError('network'))
    const { result } = setup()
    await waitFor(() => expect(result.current.viewState).toBe('ready'))

    await act(async () => result.current.handleSelectPhoto('dish', createFile()))

    expect(result.current.records[1]).toMatchObject({ status: 'failed', canRetry: true })
  })

  it('keeps the newest revision when an older response arrives later', async () => {
    mocks.put.mockResolvedValue(
      new RestResponse({ statusCode: 200, body: draftWire(2, 'Antigo', ['cuts']) }),
    )
    const { result } = setup()
    await waitFor(() => expect(result.current.viewState).toBe('ready'))

    act(() => result.current.handleChangeReflection('Antigo'))
    await act(async () => result.current.handleBlurReflection())

    await waitFor(() => expect(result.current.saveState).toBe('saved'))
    expect(onDraftStateChangeMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ revision: 3 }),
    )
  })
})

function camelDraft(revision: number, recordKeys: readonly string[]) {
  return {
    revision,
    reflection: 'Usei fogo alto.',
    photos: recordKeys.map((recordKey) => ({
      recordKey,
      photoId: `photo-${recordKey}`,
      state: 'ready',
      mediaType: 'image/jpeg',
      sizeBytes: 1200,
    })),
  }
}
