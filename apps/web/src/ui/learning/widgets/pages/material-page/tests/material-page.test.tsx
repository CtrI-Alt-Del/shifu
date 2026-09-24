import type { ComponentProps } from 'react'

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { MaterialPage } from '..'
import { useMaterialPage } from '../use-material-page'

type LinkMockProps = Omit<ComponentProps<'a'>, 'href'> & {
  params?: Record<string, string>
  to: string
}

vi.mock('@tanstack/react-router', () => ({
  Link: ({ children, params, to, ...props }: LinkMockProps) => (
    <a data-params={JSON.stringify(params)} href={to} {...props}>
      {children}
    </a>
  ),
}))
vi.mock('../use-material-page', () => ({ useMaterialPage: vi.fn() }))

const useMaterialPageMock = vi.mocked(useMaterialPage)
const IDS = {
  goalId: '01SHF000000000000000000001',
  skillId: '01SHF000000000000000000002',
  competencyId: '01SHF000000000000000000003',
  materialId: '01SHF000000000000000000004',
}

describe('MaterialPage', () => {
  afterEach(cleanup)

  it('renders official content with a route back and no completion control', () => {
    useMaterialPageMock.mockReturnValue({
      detail: {
        materialId: IDS.materialId,
        title: 'Laços',
        materialType: 'text',
        content: 'Leia e experimente\nno seu ritmo.',
      },
      isLoading: false,
      isPrivateAbsence: false,
      isRecoverableError: false,
      handleRetry: vi.fn(async () => ({}) as never),
    })
    render(<MaterialPage {...IDS} />)
    expect(screen.getByRole('heading', { name: 'Laços' })).toBeVisible()
    expect(screen.getByText(/Leia e experimente/)).toBeVisible()
    expect(
      screen.getByRole('link', { name: 'Voltar para a Competência' }),
    ).toHaveAttribute('data-params', expect.stringContaining(IDS.competencyId))
    expect(
      screen.getByText(/leitura é opcional e não altera seu progresso/i),
    ).toBeVisible()
    expect(
      screen.queryByRole('button', { name: /concluir|marcar como lido/i }),
    ).not.toBeInTheDocument()
  })
})
