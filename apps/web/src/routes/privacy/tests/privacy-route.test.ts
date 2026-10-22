import { describe, expect, it, vi } from 'vitest'

import { PrivacyPolicyPage } from '@/ui/identity/widgets/pages/privacy-policy-page'
import { Route } from '..'

const mocks = vi.hoisted(() => ({ routeOptions: null as unknown }))

vi.mock('@tanstack/react-router', () => ({
  createFileRoute: vi.fn(() => (options: unknown) => {
    mocks.routeOptions = options
    return { options }
  }),
}))

type PrivacyRouteOptions = {
  component: typeof PrivacyPolicyPage
  head: () => {
    meta: { content?: string; name?: string; title?: string }[]
  }
}

const routeOptions = () => mocks.routeOptions as PrivacyRouteOptions

describe('Privacy route', () => {
  it('registers the public policy page and its document metadata', () => {
    expect(Route).toBeDefined()
    expect(routeOptions().component).toBe(PrivacyPolicyPage)
    expect(routeOptions().head().meta).toEqual([
      { title: 'Política de privacidade — Shifu' },
      {
        name: 'description',
        content:
          'Conheça os dados tratados pelo Shifu, suas finalidades, os direitos dos titulares e como falar com a Encarregada.',
      },
    ])
  })
})
