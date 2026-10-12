import { createFileRoute } from '@tanstack/react-router'
import { handleMentorResponseStream } from '@/provision/realtime/mentor-response-stream-server-provider'
export const Route = createFileRoute(
  '/api/intelligence/mentor-sessions/$sessionId/events/',
)({
  server: {
    handlers: {
      GET: ({ request, params }) => handleMentorResponseStream(request, params.sessionId),
    },
  },
})
