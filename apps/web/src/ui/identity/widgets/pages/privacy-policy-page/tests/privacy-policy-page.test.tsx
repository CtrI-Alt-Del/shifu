import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ROUTES } from '@/constants/routes'
import type { AnchorProps } from '@/ui/shared/widgets/components/anchor'

import { PrivacyPolicyPage } from '..'

vi.mock('@/ui/shared/widgets/components/anchor', () => ({
  Anchor: ({ children, route, ...props }: AnchorProps) => (
    <a href={ROUTES[route]} {...props}>
      {typeof children === 'function' ? children({ isActive: false }) : children}
    </a>
  ),
}))

describe('PrivacyPolicyPage', () => {
  afterEach(cleanup)

  it('renders the complete policy hierarchy and privacy contact links', () => {
    render(<PrivacyPolicyPage />)

    expect(
      screen.getByRole('heading', { name: 'Política de privacidade', level: 1 }),
    ).toBeVisible()

    const sections = [
      { heading: 'Quem cuida dos seus dados', id: 'controlador' },
      { heading: 'Dados, finalidades e bases legais', id: 'dados-finalidades' },
      { heading: 'Crianças e adolescentes', id: 'criancas-adolescentes' },
      { heading: 'Cookies necessários', id: 'cookies' },
      {
        heading: 'Inteligência artificial e transferências',
        id: 'ia-transferencias',
      },
      { heading: 'Seus direitos e atendimento', id: 'direitos' },
      { heading: 'Exclusão e conservação', id: 'conservacao' },
      { heading: 'Atualizações desta política', id: 'atualizacoes' },
    ]

    for (const section of sections) {
      expect(screen.getByRole('heading', { name: section.heading })).toBeVisible()
      expect(screen.getByRole('link', { name: section.heading })).toHaveAttribute(
        'href',
        `#${section.id}`,
      )
    }

    expect(screen.getByText(/Gabriela da Silva/)).toBeVisible()
    const contactLinks = screen.getAllByRole('link', {
      name: 'shifu.ctrlaltdel@gmail.com',
    })
    expect(contactLinks).toHaveLength(3)
    expect(contactLinks[0]).toHaveAttribute(
      'href',
      expect.stringContaining('mailto:shifu.ctrlaltdel@gmail.com'),
    )
    expect(screen.getByRole('link', { name: 'Entrar' })).toHaveAttribute('href', '/login')
  })
})
