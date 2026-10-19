import { useQuery } from '@tanstack/react-query'

import { AppError } from '@/core/errors/app-error'
import { buildMentorAttachmentFilePath } from '@/constants/routes'

type MentorAttachmentFileQueryInput = {
  sessionId: string | null
  attachmentIds: string[]
  previewAttachmentIds: string[]
}
const EMPTY_FILES: Record<string, Blob> = {}
const EMPTY_ERRORS: Record<string, AppError> = {}

export const useMentorAttachmentFileQuery = ({
  sessionId,
  attachmentIds,
  previewAttachmentIds,
}: MentorAttachmentFileQueryInput) => {
  const sortedAttachmentIds = [...new Set(attachmentIds)].sort()
  const previewIds = new Set(previewAttachmentIds)
  const { data, error, isPending } = useQuery({
    queryKey: [
      'mentor-attachment-files',
      sessionId,
      sortedAttachmentIds,
      [...previewIds].sort(),
    ],
    queryFn: async ({ signal }) => {
      if (!sessionId) return {}
      const results = await Promise.all(
        sortedAttachmentIds.map(async (attachmentId) => {
          const preview = previewIds.has(attachmentId)
          const suffix = preview ? '?preview=true' : ''
          try {
            const response = await fetch(
              `${buildMentorAttachmentFilePath(sessionId, attachmentId)}${suffix}`,
              { credentials: 'same-origin', signal },
            )
            if (!response.ok) {
              const body = (await response.json().catch(() => null)) as {
                code?: string
              } | null
              return {
                attachmentId,
                error: new AppError(
                  body?.code === 'attachment_not_ready'
                    ? 'O arquivo ainda está sendo preparado.'
                    : 'Não foi possível abrir este arquivo. Tente novamente.',
                  'Erro ao abrir arquivo',
                ),
              } as const
            }
            return { attachmentId, blob: await response.blob() } as const
          } catch {
            return {
              attachmentId,
              error: new AppError(
                'Não foi possível abrir este arquivo. Tente novamente.',
                'Erro ao abrir arquivo',
              ),
            } as const
          }
        }),
      )
      return {
        files: Object.fromEntries(
          results.flatMap((result) =>
            'blob' in result ? [[result.attachmentId, result.blob]] : [],
          ),
        ) as Record<string, Blob>,
        errors: Object.fromEntries(
          results.flatMap((result) =>
            'error' in result ? [[result.attachmentId, result.error]] : [],
          ),
        ) as Record<string, AppError>,
      }
    },
    enabled: Boolean(sessionId && sortedAttachmentIds.length),
    retry: false,
    gcTime: 0,
  })

  return {
    mentorAttachmentFiles: data?.files ?? EMPTY_FILES,
    mentorAttachmentFileErrors: data?.errors ?? EMPTY_ERRORS,
    mentorAttachmentFilesError: error,
    isReadingMentorAttachmentFiles: isPending,
  }
}
