import { createFileRoute } from '@tanstack/react-router'

import { MentorAttachmentServerProvider } from '@/provision/attachments/mentor-attachment-server-provider'

const { handleMentorAttachmentFile } = MentorAttachmentServerProvider()

export const Route = createFileRoute(
  '/api/intelligence/mentor-sessions/$sessionId/attachments/$attachmentId/file/',
)({
  server: {
    handlers: {
      GET: ({ request, params, context }) =>
        handleMentorAttachmentFile(
          request,
          params.sessionId,
          params.attachmentId,
          context,
        ),
    },
  },
})
