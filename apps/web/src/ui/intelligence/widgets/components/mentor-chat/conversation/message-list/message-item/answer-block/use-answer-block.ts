import { ROUTES } from '@/constants/routes'

export type AnswerLink =
  | { kind: 'learning-goals-new' }
  | { kind: 'learning-goal'; goalId: string }
  | { kind: 'learning-skill'; goalId: string; skillId: string }
  | { kind: 'external'; href: string }
  | { kind: 'text' }

const EXTERNAL_LINK = /^https?:\/\//i
const TEXT_LINK: AnswerLink = { kind: 'text' }

// Compares a path with a route pattern segment by segment and returns the named
// params, or null when the path is not an instance of the pattern.
function matchRoute(path: string, pattern: string): Record<string, string> | null {
  const pathSegments = path.split('/')
  const patternSegments = pattern.split('/')
  if (pathSegments.length !== patternSegments.length) return null
  const params: Record<string, string> = {}
  for (const [index, patternSegment] of patternSegments.entries()) {
    const pathSegment = pathSegments[index] ?? ''
    if (patternSegment.startsWith('$')) {
      if (!pathSegment) return null
      try {
        params[patternSegment.slice(1)] = decodeURIComponent(pathSegment)
      } catch {
        return null
      }
    } else if (patternSegment !== pathSegment) return null
  }
  return params
}

export function useAnswerBlock() {
  // The closed list of internal destinations a Mentor answer may link to. Any other
  // application path renders as text so a stale or invented path never navigates.
  function resolveLink(href: string | undefined): AnswerLink {
    if (!href) return TEXT_LINK
    if (EXTERNAL_LINK.test(href)) return { kind: 'external', href }
    if (/[?#]/.test(href)) return TEXT_LINK
    if (matchRoute(href, ROUTES.learningGoalsNew)) return { kind: 'learning-goals-new' }
    const skill = matchRoute(href, ROUTES.learningSkill)
    if (skill?.goalId && skill.skillId)
      return { kind: 'learning-skill', goalId: skill.goalId, skillId: skill.skillId }
    const goal = matchRoute(href, ROUTES.learningGoal)
    if (goal?.goalId) return { kind: 'learning-goal', goalId: goal.goalId }
    return TEXT_LINK
  }

  return { resolveLink }
}
