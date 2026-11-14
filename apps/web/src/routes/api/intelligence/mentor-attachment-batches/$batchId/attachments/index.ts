import { createFileRoute } from '@tanstack/react-router'

import { MentorAttachmentServerProvider } from '@/provision/attachments/mentor-attachment-server-provider'

const { handleMentorAttachmentUpload } = MentorAttachmentServerProvider()

export const Route = createFileRoute(
  '/api/intelligence/mentor-attachment-batches/$batchId/attachments/',
)({
  server: {
    handlers: {
      POST: ({ request, params, context }) =>
        handleMentorAttachmentUpload(request, params.batchId, context),
    },
  },
})
