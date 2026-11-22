import { createFileRoute } from '@tanstack/react-router'

import { PracticePhotoServerProvider } from '@/provision/learning/practice-photo-server-provider'

const { handlePracticeDraftPhotoRead, handlePracticePhotoUpload } =
  PracticePhotoServerProvider()

export const Route = createFileRoute(
  '/api/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId/practice-photos/$recordKey/',
)({
  server: {
    handlers: {
      GET: ({ request, params, context }) =>
        handlePracticeDraftPhotoRead(request, params, params.recordKey, context),
      PUT: ({ request, params, context }) =>
        handlePracticePhotoUpload(request, params, params.recordKey, context),
    },
  },
})
