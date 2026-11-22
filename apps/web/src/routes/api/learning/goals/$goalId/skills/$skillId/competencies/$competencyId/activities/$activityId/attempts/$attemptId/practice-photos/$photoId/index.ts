import { createFileRoute } from '@tanstack/react-router'

import { PracticePhotoServerProvider } from '@/provision/learning/practice-photo-server-provider'

const { handleAttemptPracticePhotoRead } = PracticePhotoServerProvider()

export const Route = createFileRoute(
  '/api/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId/attempts/$attemptId/practice-photos/$photoId/',
)({
  server: {
    handlers: {
      GET: ({ request, params, context }) =>
        handleAttemptPracticePhotoRead(request, params, params.photoId, context),
    },
  },
})
