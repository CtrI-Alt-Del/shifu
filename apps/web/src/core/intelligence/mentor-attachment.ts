export type MentorAttachmentStatus =
  | 'uploading'
  | 'processing'
  | 'ready'
  | 'partial'
  | 'failed'
  | 'removed'

export type MentorAttachment = {
  attachmentId: string
  filename: string
  mediaType: string
  sizeBytes: number
  status: MentorAttachmentStatus
  failureCode: string | null
  analyzedPages: number[]
  illegiblePages: number[]
  uninterpretedPages: number[]
}

export type MentorAttachmentSource = {
  attachmentId: string
  chunkId: string
  pageNumber: number | null
  locator: string
}

export type MentorAttachmentBatch = {
  batchId: string
  expiresAt: string
  attachments: MentorAttachment[]
}
