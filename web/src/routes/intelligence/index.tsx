import { createFileRoute } from "@tanstack/react-router";

import { IntelligencePage } from "@/ui/intelligence/widgets/pages/intelligence-page";

export const Route = createFileRoute("/intelligence/")({
  component: IntelligencePage,
});
