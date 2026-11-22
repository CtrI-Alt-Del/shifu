import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type {
  PracticalPreparationQuestion as PracticalPreparationQuestionData,
  PracticeDraft,
} from '@/core/learning/choice-activity'

import { PracticeDraftRequestError } from '../practice-draft-request-error'
import { usePracticalPreparationQuestion } from '../use-practical-preparation-question'
import type { PracticalPreparationQuestionProps } from '../use-practical-preparation-question'
import { usePracticeDraftQuery } from '../use-practice-draft-query'
import { useRemovePracticePhotoAction } from '../use-remove-practice-photo-action'
import { useSavePracticeReflectionAction } from '../use-save-practice-reflection-action'
import { useUploadPracticePhotoAction } from '../use-upload-practice-photo-action'

vi.mock('../use-practice-draft-query', () => ({ usePracticeDraftQuery: vi.fn() }))
vi.mock('../use-save-practice-reflection-action', () => ({
  useSavePracticeReflectionAction: vi.fn(),
}))
vi.mock('../use-upload-practice-photo-action', () => ({
  useUploadPracticePhotoAction: vi.fn(),
}))
vi.mock('../use-remove-practice-photo-action', () => ({
  useRemovePracticePhotoAction: vi.fn(),
}))

const usePracticeDraftQueryMock = vi.mocked(usePracticeDraftQuery)
const useSavePracticeReflectionActionMock = vi.mocked(useSavePracticeReflectionAction)
const useUploadPracticePhotoActionMock = vi.mocked(useUploadPracticePhotoAction)
const useRemovePracticePhotoActionMock = vi.mocked(useRemovePracticePhotoAction)

const QUESTION: PracticalPreparationQuestionData = {
  key: 'practice-1',
  kind: 'practical_preparation',
  prompt: 'Prepare legumes salteados.',
  guidance: [],
  references: [],
  difficulty: 'easy',
  records: [
    { key: 'cuts', label: 'Cortes', mustShow: 'Os legumes cortados' },
    { key: 'dish', label: 'Prato final', mustShow: 'O prato pronto' },
  ],
  criteria: [{ key: 'cut', name: 'Corte', description: 'Cortes', weight: 100 }],
}

const IDS = {
  goalId: 'G'.repeat(26),
  skillId: 'S'.repeat(26),
  competencyId: 'C'.repeat(26),
  activityId: 'A'.repeat(26),
}

const FULL_DRAFT: PracticeDraft = {
  revision: 4,
  reflection: 'Usei fogo alto.',
  photos: [
    {
      recordKey: 'cuts',
      photoId: 'photo-cuts',
      state: 'ready',
      mediaType: 'image/jpeg',
      sizeBytes: 100,
    },
    {
      recordKey: 'dish',
      photoId: 'photo-dish',
      state: 'ready',
      mediaType: 'image/png',
      sizeBytes: 200,
    },
  ],
}

const EMPTY_DRAFT: PracticeDraft = { revision: 1, reflection: '', photos: [] }

const onDraftStateChangeMock = vi.fn()
const onSessionExpiredMock = vi.fn()
const reloadPracticeDraftMock = vi.fn()
const savePracticeReflectionMock = vi.fn()
const uploadPracticePhotoMock = vi.fn()
const removePracticePhotoMock = vi.fn()

function mockDraftQuery(
  practiceDraft: PracticeDraft | undefined,
  practiceDraftError: PracticeDraftRequestError | null = null,
) {
  usePracticeDraftQueryMock.mockReturnValue({
    practiceDraft,
    practiceDraftError,
    reloadPracticeDraft: reloadPracticeDraftMock,
  } as unknown as ReturnType<typeof usePracticeDraftQuery>)
}

function renderPractice(overrides: Partial<PracticalPreparationQuestionProps> = {}) {
  const initialProps: PracticalPreparationQuestionProps = {
    question: QUESTION,
    questionNumber: 1,
    totalQuestions: 1,
    ids: IDS,
    isOnlineAuthority: true,
    onDraftStateChange: onDraftStateChangeMock,
    onSessionExpired: onSessionExpiredMock,
    ...overrides,
  }
  return renderHook(
    (props: PracticalPreparationQuestionProps) => usePracticalPreparationQuestion(props),
    { initialProps },
  )
}

function createFile(name: string, size = 100, type = 'image/jpeg') {
  const file = new File(['x'], name, { type })
  Object.defineProperty(file, 'size', { value: size })
  return file
}

describe('usePracticalPreparationQuestion', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    mockDraftQuery(FULL_DRAFT)
    useSavePracticeReflectionActionMock.mockReturnValue({
      savePracticeReflection: savePracticeReflectionMock,
    })
    useUploadPracticePhotoActionMock.mockReturnValue({
      uploadPracticePhoto: uploadPracticePhotoMock,
    })
    useRemovePracticePhotoActionMock.mockReturnValue({
      removePracticePhoto: removePracticePhotoMock,
    })
    savePracticeReflectionMock.mockResolvedValue(FULL_DRAFT)
    uploadPracticePhotoMock.mockResolvedValue(FULL_DRAFT)
    removePracticePhotoMock.mockResolvedValue(EMPTY_DRAFT)
    reloadPracticeDraftMock.mockResolvedValue({ data: FULL_DRAFT })
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.clearAllMocks()
  })

  describe('view state', () => {
    it('reports an unavailable view when the Activity route is unknown', () => {
      mockDraftQuery(undefined)
      const { result } = renderPractice({ ids: null })

      expect(result.current.viewState).toBe('unavailable')
    })

    it('waits for the online session check before restoring a draft', () => {
      mockDraftQuery(undefined)
      const { result } = renderPractice({ isOnlineAuthority: false })

      expect(result.current.viewState).toBe('offline')
      expect(usePracticeDraftQueryMock).toHaveBeenCalledWith({
        ids: IDS,
        isEnabled: false,
      })
    })

    it('reports loading until the draft arrives', () => {
      mockDraftQuery(undefined)
      const { result } = renderPractice()

      expect(result.current.viewState).toBe('loading')
    })

    it('maps a load failure to a pt-BR message', () => {
      mockDraftQuery(undefined, new PracticeDraftRequestError('unavailable'))
      const { result } = renderPractice()

      expect(result.current.viewState).toBe('error')
      expect(result.current.loadErrorMessage).toBe(
        'Não foi possível carregar seu rascunho agora.',
      )
    })

    it('expires the session when the draft request is unauthorized', () => {
      mockDraftQuery(undefined, new PracticeDraftRequestError('unauthorized'))
      renderPractice()

      expect(onSessionExpiredMock).toHaveBeenCalledTimes(1)
    })

    it('reloads the draft on demand', async () => {
      mockDraftQuery(undefined, new PracticeDraftRequestError('unavailable'))
      const { result } = renderPractice()

      await act(async () => result.current.handleReloadDraft())

      expect(reloadPracticeDraftMock).toHaveBeenCalledTimes(1)
    })

    it('keeps the draft visible but locks controls when the connection is lost', () => {
      const { result } = renderPractice({ isOnlineAuthority: false })

      expect(result.current.viewState).toBe('ready')
      expect(result.current.isOffline).toBe(true)
      expect(result.current.isControlsDisabled).toBe(true)
      expect(result.current.saveStateDetail).toBe(
        'Sem conexão. As alterações só serão salvas quando a conexão voltar.',
      )
    })
  })

  describe('records and draft state', () => {
    it('restores the reflection, opens it and builds thumbnails for ready photos', () => {
      const { result } = renderPractice()

      expect(result.current.reflection).toBe('Usei fogo alto.')
      expect(result.current.isReflectionOpen).toBe(true)
      expect(result.current.records.map(({ status }) => status)).toEqual([
        'ready',
        'ready',
      ])
      expect(result.current.records[0]?.thumbnailUrl).toContain('/practice-photos/cuts')
      expect(result.current.records[0]?.thumbnailUrl).toContain('?v=photo-cuts')
      expect(result.current.saveStateLabel).toBe('Rascunho salvo na sua conta')
      expect(result.current.saveState).toBe('saved')
    })

    it('reports a complete saved draft with its revision to the page', () => {
      renderPractice()

      expect(onDraftStateChangeMock).toHaveBeenLastCalledWith({
        revision: 4,
        reflection: 'Usei fogo alto.',
        isComplete: true,
        hasUnsavedChanges: false,
      })
    })

    it('reports an incomplete draft when a record has no photo', () => {
      mockDraftQuery({ ...FULL_DRAFT, photos: [FULL_DRAFT.photos[0]] })
      const { result } = renderPractice()

      expect(result.current.records.map(({ status }) => status)).toEqual([
        'ready',
        'missing',
      ])
      expect(onDraftStateChangeMock).toHaveBeenLastCalledWith(
        expect.objectContaining({ isComplete: false }),
      )
    })

    it('treats a photo still uploading on the server as not satisfying the record', () => {
      mockDraftQuery({
        ...FULL_DRAFT,
        photos: [FULL_DRAFT.photos[0], { ...FULL_DRAFT.photos[1], state: 'uploading' }],
      })
      const { result } = renderPractice()

      expect(result.current.records[1]?.status).toBe('uploading')
      expect(onDraftStateChangeMock).toHaveBeenLastCalledWith(
        expect.objectContaining({ isComplete: false }),
      )
    })

    it('shows a server-side failed photo with a message and no thumbnail', () => {
      mockDraftQuery({
        ...FULL_DRAFT,
        photos: [FULL_DRAFT.photos[0], { ...FULL_DRAFT.photos[1], state: 'failed' }],
      })
      const { result } = renderPractice()

      expect(result.current.records[1]).toMatchObject({
        status: 'failed',
        thumbnailUrl: null,
        message: 'O envio desta foto falhou. Escolha a foto novamente.',
      })
    })

    it('does not restore the reflection a second time after later draft updates', () => {
      mockDraftQuery(FULL_DRAFT)
      const { result, rerender } = renderPractice()
      act(() => result.current.handleChangeReflection('Texto novo'))

      mockDraftQuery({ ...FULL_DRAFT, revision: 5, reflection: 'Outro texto' })
      rerender({
        question: QUESTION,
        questionNumber: 1,
        totalQuestions: 1,
        ids: IDS,
        isOnlineAuthority: true,
        onDraftStateChange: onDraftStateChangeMock,
      })

      expect(result.current.reflection).toBe('Texto novo')
    })

    it('toggles the reflection area', () => {
      mockDraftQuery(EMPTY_DRAFT)
      const { result } = renderPractice()
      expect(result.current.isReflectionOpen).toBe(false)

      act(() => result.current.handleToggleReflection())
      expect(result.current.isReflectionOpen).toBe(true)
      act(() => result.current.handleToggleReflection())
      expect(result.current.isReflectionOpen).toBe(false)
    })
  })

  describe('photo upload', () => {
    beforeEach(() => mockDraftQuery(EMPTY_DRAFT))

    it('uploads a valid photo with a UUID upload key and clears the transfer', async () => {
      const { result } = renderPractice()
      const file = createFile('cortes.jpg')

      await act(async () => result.current.handleSelectPhoto('cuts', file))

      expect(uploadPracticePhotoMock).toHaveBeenCalledWith({
        recordKey: 'cuts',
        file,
        uploadKey: expect.stringMatching(
          /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
        ),
      })
      expect(result.current.records[0]?.status).toBe('missing')
      expect(result.current.records[0]?.message).toBeNull()
    })

    it('marks the record as uploading while the request is pending', async () => {
      let resolveUpload: (draft: PracticeDraft) => void = () => undefined
      uploadPracticePhotoMock.mockReturnValue(
        new Promise<PracticeDraft>((resolve) => {
          resolveUpload = resolve
        }),
      )
      const { result } = renderPractice()

      act(() => {
        void result.current.handleSelectPhoto('cuts', createFile('cortes.jpg'))
      })

      expect(result.current.records[0]?.status).toBe('uploading')
      expect(result.current.records[0]?.fileName).toBe('cortes.jpg')
      expect(result.current.saveState).toBe('saving')
      expect(result.current.saveStateLabel).toBe('Salvando rascunho…')
      await act(async () => resolveUpload(FULL_DRAFT))
      expect(result.current.records[0]?.status).toBe('missing')
    })

    it.each([
      [
        'an empty file',
        createFile('vazio.jpg', 0),
        'O arquivo está vazio. Escolha outra foto.',
      ],
      [
        'a file above 10 MB',
        createFile('grande.jpg', 10 * 1024 * 1024 + 1),
        'A foto excede 10 MB. Escolha uma foto menor.',
      ],
      [
        'a file with an unsupported extension',
        createFile('nota.pdf', 100, 'application/pdf'),
        'Este arquivo não é uma foto JPEG, PNG ou WebP.',
      ],
    ])('rejects %s without sending it', async (_label, file, message) => {
      const { result } = renderPractice()

      await act(async () => result.current.handleSelectPhoto('cuts', file))

      expect(uploadPracticePhotoMock).not.toHaveBeenCalled()
      expect(result.current.records[0]).toMatchObject({
        status: 'failed',
        message,
        canRetry: false,
      })
    })

    it('accepts a photo of exactly 10 MB', async () => {
      const { result } = renderPractice()

      await act(async () =>
        result.current.handleSelectPhoto(
          'cuts',
          createFile('limite.webp', 10 * 1024 * 1024, 'image/webp'),
        ),
      )

      expect(uploadPracticePhotoMock).toHaveBeenCalledTimes(1)
    })

    it('keeps a retryable failure and retries with the same upload key', async () => {
      uploadPracticePhotoMock.mockRejectedValueOnce(
        new PracticeDraftRequestError('unavailable'),
      )
      const { result } = renderPractice()
      const file = createFile('cortes.png', 100, 'image/png')

      await act(async () => result.current.handleSelectPhoto('cuts', file))
      expect(result.current.records[0]).toMatchObject({
        status: 'failed',
        canRetry: true,
        message: 'Não foi possível enviar a foto. Tente novamente.',
      })
      await act(async () => result.current.handleRetryPhoto('cuts'))

      expect(uploadPracticePhotoMock).toHaveBeenCalledTimes(2)
      expect(uploadPracticePhotoMock.mock.calls[1]?.[0].uploadKey).toBe(
        uploadPracticePhotoMock.mock.calls[0]?.[0].uploadKey,
      )
      expect(result.current.records[0]?.status).toBe('missing')
    })

    it('does not offer a retry when the server rejects the file size', async () => {
      uploadPracticePhotoMock.mockRejectedValueOnce(
        new PracticeDraftRequestError('too-large'),
      )
      const { result } = renderPractice()

      await act(async () => result.current.handleSelectPhoto('cuts', createFile('a.jpg')))

      expect(result.current.records[0]).toMatchObject({
        status: 'failed',
        canRetry: false,
        message: 'A foto excede 10 MB. Escolha uma foto menor.',
      })
      await act(async () => result.current.handleRetryPhoto('cuts'))
      expect(uploadPracticePhotoMock).toHaveBeenCalledTimes(1)
    })

    it('maps a server-side unsupported file failure', async () => {
      uploadPracticePhotoMock.mockRejectedValueOnce(
        new PracticeDraftRequestError('unsupported'),
      )
      const { result } = renderPractice()

      await act(async () => result.current.handleSelectPhoto('cuts', createFile('a.jpg')))

      expect(result.current.records[0]?.message).toBe(
        'Este arquivo não é uma foto JPEG, PNG ou WebP válida.',
      )
    })

    it('expires the session when the upload is unauthorized', async () => {
      uploadPracticePhotoMock.mockRejectedValueOnce(
        new PracticeDraftRequestError('unauthorized'),
      )
      const { result } = renderPractice()

      await act(async () => result.current.handleSelectPhoto('cuts', createFile('a.jpg')))

      expect(onSessionExpiredMock).toHaveBeenCalledTimes(1)
    })

    it('treats an unexpected error as a retryable failure', async () => {
      uploadPracticePhotoMock.mockRejectedValueOnce(new Error('boom'))
      const { result } = renderPractice()

      await act(async () => result.current.handleSelectPhoto('cuts', createFile('a.jpg')))

      expect(result.current.records[0]?.canRetry).toBe(true)
    })

    it('ignores selection and retry while the controls are disabled', async () => {
      const { result } = renderPractice({ disabled: true })

      await act(async () => result.current.handleSelectPhoto('cuts', createFile('a.jpg')))
      await act(async () => result.current.handleRetryPhoto('cuts'))
      await act(async () => result.current.handleRemovePhoto('cuts'))

      expect(uploadPracticePhotoMock).not.toHaveBeenCalled()
      expect(removePracticePhotoMock).not.toHaveBeenCalled()
    })

    it('keeps the previous photo and a message when a replacement fails', async () => {
      mockDraftQuery(FULL_DRAFT)
      uploadPracticePhotoMock.mockRejectedValueOnce(
        new PracticeDraftRequestError('unavailable'),
      )
      const { result } = renderPractice()

      await act(async () =>
        result.current.handleSelectPhoto('cuts', createFile('nova.jpg')),
      )

      expect(result.current.records[0]).toMatchObject({
        status: 'ready',
        message: 'Não foi possível enviar a foto. Tente novamente.',
        canRetry: true,
      })
      expect(result.current.records[0]?.thumbnailUrl).not.toBeNull()
    })
  })

  describe('photo removal', () => {
    it('removes a photo and clears the transfer', async () => {
      const { result } = renderPractice()

      await act(async () => result.current.handleRemovePhoto('cuts'))

      expect(removePracticePhotoMock).toHaveBeenCalledWith('cuts')
      expect(result.current.records[0]?.message).toBeNull()
    })

    it('marks the record as removing while the request is pending', async () => {
      let resolveRemoval: (draft: PracticeDraft) => void = () => undefined
      removePracticePhotoMock.mockReturnValue(
        new Promise<PracticeDraft>((resolve) => {
          resolveRemoval = resolve
        }),
      )
      const { result } = renderPractice()

      act(() => {
        void result.current.handleRemovePhoto('cuts')
      })
      expect(result.current.records[0]?.status).toBe('removing')
      await act(async () => resolveRemoval(EMPTY_DRAFT))
    })

    it('reports a removal failure without a retry shortcut', async () => {
      removePracticePhotoMock.mockRejectedValueOnce(
        new PracticeDraftRequestError('unavailable'),
      )
      const { result } = renderPractice()

      await act(async () => result.current.handleRemovePhoto('cuts'))

      expect(result.current.records[0]).toMatchObject({
        message: 'Não foi possível remover a foto. Tente novamente.',
        canRetry: false,
      })
    })

    it('expires the session when removal is unauthorized', async () => {
      removePracticePhotoMock.mockRejectedValueOnce(
        new PracticeDraftRequestError('unauthorized'),
      )
      const { result } = renderPractice()

      await act(async () => result.current.handleRemovePhoto('cuts'))

      expect(onSessionExpiredMock).toHaveBeenCalledTimes(1)
    })
  })

  describe('reflection autosave', () => {
    it('saves the latest text after the autosave delay and reports it as saved', async () => {
      const { result } = renderPractice()

      act(() => result.current.handleChangeReflection('Primeiro'))
      act(() => result.current.handleChangeReflection('Primeiro e segundo'))
      expect(result.current.saveStateLabel).toBe('Salvando rascunho…')
      expect(onDraftStateChangeMock).toHaveBeenLastCalledWith(
        expect.objectContaining({ hasUnsavedChanges: true }),
      )
      expect(savePracticeReflectionMock).not.toHaveBeenCalled()
      await act(async () => {
        await vi.advanceTimersByTimeAsync(800)
      })

      expect(savePracticeReflectionMock).toHaveBeenCalledTimes(1)
      expect(savePracticeReflectionMock).toHaveBeenCalledWith('Primeiro e segundo')
      expect(result.current.saveStateLabel).toBe('Rascunho salvo na sua conta')
      expect(onDraftStateChangeMock).toHaveBeenLastCalledWith(
        expect.objectContaining({ hasUnsavedChanges: false }),
      )
    })

    it('flushes a pending save when the field loses focus', async () => {
      const { result } = renderPractice()

      act(() => result.current.handleChangeReflection('Texto'))
      await act(async () => result.current.handleBlurReflection())

      expect(savePracticeReflectionMock).toHaveBeenCalledWith('Texto')
    })

    it('does nothing on blur when there is no pending change', async () => {
      const { result } = renderPractice()

      await act(async () => result.current.handleBlurReflection())

      expect(savePracticeReflectionMock).not.toHaveBeenCalled()
    })

    it('shows Não salvo after a failed save and keeps the text', async () => {
      savePracticeReflectionMock.mockRejectedValueOnce(
        new PracticeDraftRequestError('unavailable'),
      )
      const { result } = renderPractice()

      act(() => result.current.handleChangeReflection('Texto'))
      await act(async () => {
        await vi.advanceTimersByTimeAsync(800)
      })

      expect(result.current.saveState).toBe('failed')
      expect(result.current.saveStateLabel).toBe('Rascunho não salvo')
      expect(result.current.saveStateDetail).toBe(
        'Tente novamente antes de sair. As últimas alterações ainda não estão salvas na sua conta.',
      )
      expect(result.current.reflection).toBe('Texto')
      expect(onDraftStateChangeMock).toHaveBeenLastCalledWith(
        expect.objectContaining({ hasUnsavedChanges: true }),
      )
    })

    it('retries a failed save with the latest text', async () => {
      savePracticeReflectionMock.mockRejectedValueOnce(
        new PracticeDraftRequestError('unavailable'),
      )
      const { result } = renderPractice()

      act(() => result.current.handleChangeReflection('Texto'))
      await act(async () => {
        await vi.advanceTimersByTimeAsync(800)
      })
      await act(async () => result.current.handleRetrySaveReflection())

      expect(savePracticeReflectionMock).toHaveBeenCalledTimes(2)
      expect(result.current.saveState).toBe('saved')
    })

    it('expires the session when saving is unauthorized', async () => {
      savePracticeReflectionMock.mockRejectedValueOnce(
        new PracticeDraftRequestError('unauthorized'),
      )
      const { result } = renderPractice()

      act(() => result.current.handleChangeReflection('Texto'))
      await act(async () => {
        await vi.advanceTimersByTimeAsync(800)
      })

      expect(onSessionExpiredMock).toHaveBeenCalledTimes(1)
    })

    it('queues a second save while the first is in flight', async () => {
      let resolveFirst: (draft: PracticeDraft) => void = () => undefined
      savePracticeReflectionMock.mockReturnValueOnce(
        new Promise<PracticeDraft>((resolve) => {
          resolveFirst = resolve
        }),
      )
      const { result } = renderPractice()

      act(() => result.current.handleChangeReflection('um'))
      await act(async () => {
        await vi.advanceTimersByTimeAsync(800)
      })
      act(() => result.current.handleChangeReflection('um dois'))
      await act(async () => {
        await vi.advanceTimersByTimeAsync(800)
      })
      expect(savePracticeReflectionMock).toHaveBeenCalledTimes(1)
      await act(async () => resolveFirst(FULL_DRAFT))

      expect(savePracticeReflectionMock).toHaveBeenCalledTimes(2)
      expect(savePracticeReflectionMock).toHaveBeenLastCalledWith('um dois')
      expect(result.current.saveState).toBe('saved')
    })

    it('ignores reflection edits while the controls are disabled', () => {
      const { result } = renderPractice({ disabled: true })

      act(() => result.current.handleChangeReflection('Bloqueado'))

      expect(result.current.reflection).toBe('Usei fogo alto.')
      expect(savePracticeReflectionMock).not.toHaveBeenCalled()
    })
  })

  describe('draft conflict', () => {
    it('reloads the saved draft, replaces local edits and explains the conflict', async () => {
      reloadPracticeDraftMock.mockResolvedValue({
        data: { ...FULL_DRAFT, revision: 9, reflection: 'Versão do outro dispositivo' },
      })
      const { result, rerender } = renderPractice()
      act(() => result.current.handleChangeReflection('Edição local'))

      await act(async () => {
        rerender({
          question: QUESTION,
          questionNumber: 1,
          totalQuestions: 1,
          ids: IDS,
          isOnlineAuthority: true,
          onDraftStateChange: onDraftStateChangeMock,
          conflictCount: 1,
        })
      })

      expect(reloadPracticeDraftMock).toHaveBeenCalledTimes(1)
      expect(result.current.reflection).toBe('Versão do outro dispositivo')
      expect(result.current.notice).toBe('conflict')
      expect(result.current.saveState).toBe('saved')
    })

    it('keeps the current draft when the reload returns no data', async () => {
      reloadPracticeDraftMock.mockResolvedValue({ data: undefined })
      const { result, rerender } = renderPractice()

      await act(async () => {
        rerender({
          question: QUESTION,
          questionNumber: 1,
          totalQuestions: 1,
          ids: IDS,
          isOnlineAuthority: true,
          onDraftStateChange: onDraftStateChangeMock,
          conflictCount: 1,
        })
      })

      expect(result.current.notice).toBeNull()
      expect(result.current.reflection).toBe('Usei fogo alto.')
    })

    it('clears the conflict notice when the learner edits again', async () => {
      const { result, rerender } = renderPractice()
      await act(async () => {
        rerender({
          question: QUESTION,
          questionNumber: 1,
          totalQuestions: 1,
          ids: IDS,
          isOnlineAuthority: true,
          onDraftStateChange: onDraftStateChangeMock,
          conflictCount: 1,
        })
      })
      expect(result.current.notice).toBe('conflict')

      act(() => result.current.handleChangeReflection('Nova edição'))

      expect(result.current.notice).toBeNull()
    })
  })
})
