import { useMutation, useQueryClient } from '@tanstack/react-query'

import { HTTP_STATUS_CODE } from '@/constants/http-status-code'
import { buildPracticePhotoPath } from '@/constants/routes'
import type { PracticeDraft } from '@/core/learning/choice-activity'

import { keepNewestPracticeDraft } from './keep-newest-practice-draft'
import {
  type PracticeDraftErrorKind,
  PracticeDraftRequestError,
} from './practice-draft-request-error'
import type { PracticeDraftIds } from './practice-draft-server-functions'
import { practiceDraftQueryKey } from './use-practice-draft-query'

export type UploadPracticePhotoInput = {
  recordKey: string
  file: File
  uploadKey: string
}

export const useUploadPracticePhotoAction = (ids: PracticeDraftIds | null) => {
  const queryClient = useQueryClient()
  const { mutateAsync: uploadPracticePhoto } = useMutation({
    mutationFn: async ({ recordKey, file, uploadKey }: UploadPracticePhotoInput) => {
      if (!ids) throw new PracticeDraftRequestError('invalid-request')
      const formData = new FormData()
      formData.append('file', file, file.name)
      formData.append('upload_key', uploadKey)
      let response: Response
      try {
        response = await fetch(buildPracticePhotoPath({ ...ids, recordKey }), {
          method: 'PUT',
          body: formData,
          credentials: 'same-origin',
        })
      } catch {
        throw new PracticeDraftRequestError('unavailable')
      }
      if (!response.ok)
        throw new PracticeDraftRequestError(
          failureKind(response.status, await readFailureCode(response)),
        )
      return (await response.json()) as PracticeDraft
    },
    onSuccess: (draft: PracticeDraft) => {
      queryClient.setQueryData<PracticeDraft>(practiceDraftQueryKey(ids), (current) =>
        keepNewestPracticeDraft(current, draft),
      )
    },
  })

  return { uploadPracticePhoto }
}

async function readFailureCode(response: Response): Promise<string | undefined> {
  try {
    const body = (await response.json()) as { code?: unknown }
    return typeof body.code === 'string' ? body.code : undefined
  } catch {
    return undefined
  }
}

function failureKind(
  statusCode: number,
  code: string | undefined,
): PracticeDraftErrorKind {
  if (statusCode === HTTP_STATUS_CODE.unauthorized) return 'unauthorized'
  if (statusCode === HTTP_STATUS_CODE.notFound) return 'not-found'
  if (statusCode === HTTP_STATUS_CODE.conflict) {
    if (code === 'upload_key_conflict') return 'upload-key-conflict'
    if (code === 'conflict') return 'evaluation-pending'
    if (code === 'practice_draft_closed') return 'draft-closed'
    return 'unavailable'
  }
  if (statusCode === HTTP_STATUS_CODE.payloadTooLarge) return 'too-large'
  if (statusCode === HTTP_STATUS_CODE.unprocessableEntity) return 'unsupported'
  return 'unavailable'
}
