import { createFileRoute } from '@tanstack/react-router'

import { LearningPage } from '@/ui/learning/widgets/pages/learning-page'

export const Route = createFileRoute('/learning/')({ component: LearningPage })
