import { cleanup, render, screen } from '@testing-library/react'
import type { ComponentProps } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ROUTES } from '@/constants/routes'
import { Anchor } from '..'

const mocks = vi.hoisted(() => ({
  link: vi.fn(),
}))

vi.mock('@tanstack/react-router', () => ({
  Link: (props: Record<string, unknown>) => {
    mocks.link(props)
    return <a href={String(props.to)}>{props.children as string}</a>
  },
}))

describe('Anchor', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('links to the canonical path of the named route', () => {
    render(<Anchor route='intelligenceMemories'>Memórias</Anchor>)

    expect(screen.getByRole('link', { name: 'Memórias' })).toHaveAttribute(
      'href',
      ROUTES.intelligenceMemories,
    )
    expect(mocks.link).toHaveBeenCalledWith(
      expect.objectContaining({ to: ROUTES.intelligenceMemories, search: undefined }),
    )
  })

  it('forwards search values and link props to the router link', () => {
    const search = { session: '01J7T8AC91Z5K8M4JQ8C2D6F0B', message: undefined }
    const props: ComponentProps<typeof Anchor> = {
      route: 'intelligence',
      search,
      className: 'link',
      children: 'Abrir conversa',
    }

    render(<Anchor {...props} />)

    expect(mocks.link).toHaveBeenCalledWith(
      expect.objectContaining({ to: ROUTES.intelligence, search, className: 'link' }),
    )
  })
})
