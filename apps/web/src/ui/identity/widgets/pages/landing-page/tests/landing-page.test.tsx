import { cleanup, render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ROUTES } from '@/constants/routes'

import { LandingPage } from '..'
import { useLandingPage } from '../use-landing-page'

vi.mock('../use-landing-page', () => ({
  useLandingPage: vi.fn(),
}))

vi.mock('@/ui/shared/widgets/components/anchor', () => ({
  Anchor: ({
    children,
    route,
    ...props
  }: {
    children: ReactNode
    route: keyof typeof ROUTES
    [key: string]: unknown
  }) => (
    <a href={ROUTES[route]} {...props}>
      {children}
    </a>
  ),
}))

const useLandingPageMock = vi.mocked(useLandingPage)

describe('LandingPage', () => {
  beforeEach(() => {
    useLandingPageMock.mockReturnValue({ isDocumentVisible: true })
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('explains the learning journey and guides visitors to existing account routes', () => {
    render(<LandingPage />)

    expect(
      screen.getByRole('heading', {
        level: 1,
        name: 'Veja sua evolução no que você quer aprender.',
      }),
    ).toBeVisible()
    expect(screen.getByText(/diagnóstico ajuda a entender/)).toBeVisible()
    expect(screen.getByRole('heading', { name: /Uma pista na hora certa/ })).toBeVisible()
    expect(
      screen.getByText(/sua jornada continua útil mesmo quando ela não está disponível/),
    ).toBeVisible()
    expect(screen.getByRole('link', { name: 'Entrar' })).toHaveAttribute(
      'href',
      ROUTES.login,
    )
    expect(screen.getAllByRole('link', { name: /Criar conta/ })).toHaveLength(3)
    expect(screen.getAllByRole('link', { name: /Criar conta/ })[0]).toHaveAttribute(
      'href',
      ROUTES.register,
    )
    expect(screen.getAllByRole('link', { name: /privacidade/i })).toHaveLength(2)
    expect(
      screen.getAllByRole('link', { name: /Aviso de privacidade/ })[0],
    ).toHaveAttribute('href', ROUTES.privacy)
  })

  it('labels the preview as illustrative and distinguishes current and future topics', () => {
    render(<LandingPage />)

    expect(screen.getByLabelText('Exemplo ilustrativo de evolução')).toBeVisible()
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '50')
    expect(
      screen.getAllByRole('heading', { name: 'Lógica de Programação' }),
    ).toHaveLength(2)
    expect(screen.getByText('Culinária').closest('article')).toHaveTextContent('Em breve')
    expect(screen.getByText('Idiomas').closest('article')).toHaveTextContent('Em breve')
    expect(
      screen.queryByText(/pratique todos os dias|no seu ritmo, passo a passo/i),
    ).toBeNull()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('enables only decorative motion while the document is visible', () => {
    const { container } = render(<LandingPage />)

    expect(container.firstElementChild).toHaveAttribute('data-motion-enabled', 'true')
  })
})
