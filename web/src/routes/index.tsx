import { createFileRoute } from "@tanstack/react-router";

import { DashboardPage } from "@/ui/shared/widgets/pages/dashboard-page";

export const Route = createFileRoute("/")({ component: DashboardPage });
