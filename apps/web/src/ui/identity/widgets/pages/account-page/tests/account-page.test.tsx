import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ROUTES } from '@/constants/routes'
import type { AnchorProps } from '@/ui/shared/widgets/components/anchor'

import { AccountPage } from '..'

vi.mock('@/ui/shared/widgets/components/anchor', () => ({
  Anchor: ({ children, route, ...props }: AnchorProps) => (
    <a href={ROUTES[route]} {...props}>
      {typeof children === 'function' ? children({ isActive: false }) : children}
    </a>
  ),
}))

describe('AccountPage', () => {
  afterEach(cleanup)

  it('shows the privacy destination alongside the existing account settings', () => {
    render(<AccountPage />)

    expect(screen.getByRole('heading', { name: 'Minha conta' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Dados da conta' })).toBeVisible()
    expect(
      screen.getByRole('heading', { name: 'Preferências de aprendizagem' }),
    ).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Privacidade' })).toBeVisible()
    expect(
      screen.getByRole('link', { name: 'Ler política de privacidade' }),
    ).toHaveAttribute('href', ROUTES.privacy)
    expect(screen.getAllByText('Em preparação')).toHaveLength(2)
  })
})
