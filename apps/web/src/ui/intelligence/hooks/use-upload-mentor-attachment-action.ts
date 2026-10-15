import { useMutation } from '@tanstack/react-query'

import { AppError } from '@/core/errors/app-error'
import type { MentorAttachment } from '@/core/intelligence/mentor-attachment'
import { buildMentorAttachmentUploadPath } from '@/constants/routes'

type UploadMentorAttachmentInput = {
  batchId: string
  uploadKey: string
  file: File
  signal?: AbortSignal
}

const FAILURE_MESSAGES: Record<string, string> = {
  attachment_too_large: 'O arquivo excede o limite de 10 MB.',
  unsupported_attachment: 'Este formato de arquivo não é aceito.',
  malformed_attachment: 'Não foi possível ler este arquivo.',
  attachment_batch_expired:
    'A preparação expirou. Remova e adicione o arquivo novamente.',
  attachment_batch_consumed: 'Esta preparação já foi enviada. Inicie uma nova mensagem.',
  attachment_divergent_replay:
    'O arquivo mudou durante o envio. Remova e adicione novamente.',
  unauthenticated: 'Sua sessão expirou. Atualize a página.',
  inactive_account: 'Sua conta não pode enviar arquivos no momento.',
}

export const useUploadMentorAttachmentAction = () => {
  const { error, isPending, mutateAsync } = useMutation({
    mutationFn: async ({
      batchId,
      file,
      uploadKey,
      signal,
    }: UploadMentorAttachmentInput) => {
      const formData = new FormData()
      formData.append('file', file, file.name)
      formData.append('upload_key', uploadKey)
      const response = await fetch(buildMentorAttachmentUploadPath(batchId), {
        method: 'POST',
        body: formData,
        credentials: 'same-origin',
        signal,
      })
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { code?: string } | null
        const message = body?.code ? FAILURE_MESSAGES[body.code] : undefined
        throw new AppError(
          message ?? 'Não foi possível enviar o arquivo. Tente novamente.',
          'Erro ao enviar arquivo',
        )
      }
      return (await response.json()) as MentorAttachment
    },
  })

  return {
    uploadMentorAttachment: mutateAsync,
    uploadMentorAttachmentError: error,
    isUploadingMentorAttachment: isPending,
  }
}
