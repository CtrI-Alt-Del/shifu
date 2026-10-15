import { createFileRoute } from '@tanstack/react-router'

import { handleMentorAttachmentUpload } from '@/provision/attachments/mentor-attachment-server-provider'

export const Route = createFileRoute(
  '/api/intelligence/mentor-attachment-batches/$batchId/attachments/',
)({
  server: {
    handlers: {
      POST: ({ request, params }) =>
        handleMentorAttachmentUpload(request, params.batchId),
    },
  },
})
