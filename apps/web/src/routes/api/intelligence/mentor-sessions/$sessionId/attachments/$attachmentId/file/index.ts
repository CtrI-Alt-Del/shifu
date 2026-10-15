import { createFileRoute } from '@tanstack/react-router'

import { handleMentorAttachmentFile } from '@/provision/attachments/mentor-attachment-server-provider'

export const Route = createFileRoute(
  '/api/intelligence/mentor-sessions/$sessionId/attachments/$attachmentId/file/',
)({
  server: {
    handlers: {
      GET: ({ request, params }) =>
        handleMentorAttachmentFile(request, params.sessionId, params.attachmentId),
    },
  },
})
