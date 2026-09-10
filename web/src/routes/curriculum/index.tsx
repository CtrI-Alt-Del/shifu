import { createFileRoute } from "@tanstack/react-router";

import { CurriculumPage } from "@/ui/curriculum/widgets/pages/curriculum-page";

export const Route = createFileRoute("/curriculum/")({
  component: CurriculumPage,
});
