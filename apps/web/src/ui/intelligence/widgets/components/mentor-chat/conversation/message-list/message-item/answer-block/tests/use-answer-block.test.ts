import { renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { ROUTES } from '@/constants/routes'
import { useAnswerBlock } from '../use-answer-block'

const GOAL_ID = '01J7T8AC91Z5K8M4JQ8C2D6F00'
const SKILL_ID = '01J7T8AC91Z5K8M4JQ8C2D6F01'

function resolve(href: string | undefined) {
  const { result } = renderHook(() => useAnswerBlock())
  return result.current.resolveLink(href)
}

describe('useAnswerBlock', () => {
  it('resolves the Objective creation path to its canonical route', () => {
    expect(resolve(ROUTES.learningGoalsNew)).toEqual({ kind: 'learning-goals-new' })
  })

  it('resolves an Objective path to the route params instead of a string path', () => {
    expect(resolve(`/learning/goals/${GOAL_ID}`)).toEqual({
      kind: 'learning-goal',
      goalId: GOAL_ID,
    })
  })

  it('resolves a Skill path to both explicit params', () => {
    expect(resolve(`/learning/goals/${GOAL_ID}/skills/${SKILL_ID}`)).toEqual({
      kind: 'learning-skill',
      goalId: GOAL_ID,
      skillId: SKILL_ID,
    })
  })

  it('does not mistake the creation path for an Objective identifier', () => {
    expect(resolve('/learning/goals/new')).toEqual({ kind: 'learning-goals-new' })
  })

  it('decodes encoded params', () => {
    expect(resolve('/learning/goals/a%20b')).toEqual({
      kind: 'learning-goal',
      goalId: 'a b',
    })
  })

  it.each([
    ['an unknown application path', '/gamification'],
    ['a nested path outside the closed list', `/learning/goals/${GOAL_ID}/settings`],
    ['a path with a trailing slash', `/learning/goals/${GOAL_ID}/`],
    ['a path with a query string', `/learning/goals/${GOAL_ID}?tab=lista`],
    ['a path with a hash', `/learning/goals/${GOAL_ID}#skills`],
    ['a protocol-relative URL', '//example.com/learning/goals/x'],
    ['a malformed escape', '/learning/goals/%E0%A4%A'],
    ['a relative path', 'learning/goals/new'],
    ['a mailto link', 'mailto:aluno@example.com'],
    ['an empty href', ''],
    ['a missing href', undefined],
  ])('renders %s as text', (_label, href) => {
    expect(resolve(href)).toEqual({ kind: 'text' })
  })

  it.each(['https://example.com/ajuda', 'http://example.com', 'HTTPS://EXAMPLE.COM'])(
    'keeps the external link %s as a native anchor',
    (href) => {
      expect(resolve(href)).toEqual({ kind: 'external', href })
    },
  )
})
