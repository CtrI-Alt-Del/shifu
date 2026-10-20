/**
 * Plannings opened from the Home composer during this page session.
 *
 * The marker lives only in memory on purpose: reloading, closing or opening the
 * planner through a direct link loses it, and the page then abandons the planning
 * instead of restoring it (Intelligence JN-12).
 */
const openedPlannings = new Set<string>()

export function registerPlanningEntry(planningId: string): void {
  openedPlannings.add(planningId)
}

export function consumePlanningEntry(planningId: string): boolean {
  return openedPlannings.delete(planningId)
}
