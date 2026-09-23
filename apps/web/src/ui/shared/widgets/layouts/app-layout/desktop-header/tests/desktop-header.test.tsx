import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ROUTES } from '@/constants/routes'
import type { AnchorProps } from '@/ui/shared/widgets/components/anchor'
import type { IconProps } from '@/ui/shared/widgets/components/icon'

import { DesktopHeader } from '..'
import { APP_NAVIGATION_ITEMS } from '../../use-app-layout'

vi.mock('@/ui/shared/widgets/components/anchor', () => ({
  Anchor: ({ children, route, ...props }: AnchorProps) => (
    <a href={ROUTES[route]} {...props}>
      {typeof children === 'function' ? children({ isActive: false }) : children}
    </a>
  ),
}))

vi.mock('@/ui/shared/widgets/components/icon', () => ({
  Icon: ({ name }: IconProps) => <span aria-hidden='true'>{name}</span>,
}))

describe('DesktopHeader', () => {
  afterEach(cleanup)

  it('renders the brand and marks the active primary destination', () => {
    render(<DesktopHeader items={APP_NAVIGATION_ITEMS} pathname='/gamification' />)

    expect(screen.getByRole('link', { name: 'Shifu — Objetivos' })).toHaveAttribute(
      'href',
      ROUTES.root,
    )
    expect(screen.getByRole('link', { name: 'Objetivos' })).toHaveAttribute(
      'href',
      ROUTES.root,
    )
    expect(screen.getByRole('link', { name: 'Progresso' })).toHaveAttribute(
      'aria-current',
      'page',
    )
    expect(screen.getByRole('link', { name: 'Mentor' })).toHaveAttribute(
      'href',
      ROUTES.intelligence,
    )
  })

  it('renders the default account trigger and accepts a custom account menu', () => {
    const { rerender } = render(
      <DesktopHeader items={APP_NAVIGATION_ITEMS} pathname={ROUTES.root} />,
    )

    expect(screen.getByRole('button', { name: 'Abrir menu da conta' })).toBeVisible()

    rerender(
      <DesktopHeader
        accountMenu={<button type='button'>Conta personalizada</button>}
        items={APP_NAVIGATION_ITEMS}
        pathname={ROUTES.root}
      />,
    )

    expect(screen.getByRole('button', { name: 'Conta personalizada' })).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Abrir menu da conta' })).toBeNull()
  })
})
