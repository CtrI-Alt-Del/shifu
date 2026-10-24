import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { createRef } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { MentorActionCard, type MentorActionCardProps } from '..'

const onSelectMock = vi.fn()

function renderCard(overrides: Partial<MentorActionCardProps> = {}) {
  return render(
    <MentorActionCard
      actions={[]}
      icon={{ name: 'graduation-cap', tone: 'jade' }}
      title='Adicionar Funções em Python?'
      {...overrides}
    />,
  )
}

describe('MentorActionCard', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('renders the proposal anatomy with its title, destination, reason and consequences', () => {
    renderCard({
      title: 'Remover Funções em Python?',
      destination: 'Objetivo: Aprender a programar',
      reason: 'Você pediu para retirar esta Habilidade do Objetivo.',
      consequences: 'Não há restauração.',
      icon: { name: 'trash-2', tone: 'danger' },
    })

    expect(
      screen.getByRole('region', { name: 'Remover Funções em Python?' }),
    ).toBeVisible()
    expect(
      screen.getByRole('heading', { level: 3, name: 'Remover Funções em Python?' }),
    ).toBeVisible()
    expect(screen.getByText('Objetivo: Aprender a programar')).toBeVisible()
    expect(
      screen.getByText('Você pediu para retirar esta Habilidade do Objetivo.'),
    ).toBeVisible()
    expect(screen.getByText('Não há restauração.')).toBeVisible()
    expect(screen.queryByRole('button')).toBeNull()
  })

  it('announces the result and the status line through one status region', () => {
    const resultRef = createRef<HTMLDivElement>()
    renderCard({
      title: 'Funções em Python removida',
      result: 'A experiência e seu histórico foram removidos.',
      statusText: 'Remoção concluída',
      resultRef,
    })

    const status = screen.getByRole('status')
    expect(status).toHaveTextContent('A experiência e seu histórico foram removidos.')
    expect(status).toHaveTextContent('Remoção concluída')
    expect(resultRef.current).toBe(status)
    expect(status).toHaveAttribute('tabindex', '-1')
  })

  it('keeps an empty status region available for later announcements', () => {
    renderCard()

    expect(screen.getByRole('status')).toBeEmptyDOMElement()
  })

  it('keeps the title available to assistive technology when it is not visible', () => {
    renderCard({ isTitleVisible: false })

    expect(
      screen.getByRole('heading', { level: 3, name: 'Adicionar Funções em Python?' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 3 }).parentElement).toHaveClass('sr-only')
  })

  it('renders every action variant as a keyboard operable button of at least 44 px', () => {
    renderCard({
      actions: [
        { key: 'decline', label: 'Recusar', variant: 'outline', onSelect: onSelectMock },
        {
          key: 'confirm',
          label: 'Remover habilidade',
          variant: 'danger',
          onSelect: onSelectMock,
        },
        { key: 'retry', label: 'Tentar novamente', variant: 'primary', disabled: true },
      ],
    })

    const decline = screen.getByRole('button', { name: 'Recusar' })
    const confirm = screen.getByRole('button', { name: 'Remover habilidade' })
    const retry = screen.getByRole('button', { name: 'Tentar novamente' })
    fireEvent.click(decline)
    fireEvent.click(confirm)
    expect(onSelectMock).toHaveBeenCalledTimes(2)
    expect(retry).toBeDisabled()
    for (const button of [decline, confirm, retry]) {
      expect(button).toHaveAttribute('type', 'button')
      expect(button).toHaveClass('min-h-11')
    }
  })

  it('stacks the actions at full width below 480 px', () => {
    renderCard({
      actions: [
        { key: 'decline', label: 'Recusar', variant: 'outline', onSelect: onSelectMock },
        { key: 'confirm', label: 'Adicionar habilidade', variant: 'primary' },
      ],
    })

    const row = screen.getByRole('button', { name: 'Recusar' }).parentElement
    expect(row).toHaveClass('max-[480px]:flex-col')
    expect(row).toHaveClass('max-[480px]:[&>*]:w-full')
    expect(row).toHaveClass('justify-end')
  })

  it('renders a link action inside the same row with the button styling it receives', () => {
    renderCard({
      actions: [
        {
          key: 'view',
          label: 'Ver Objetivo',
          variant: 'outline',
          renderLink: (className) => (
            <a className={className} href='/learning/goals/goal-1'>
              Ver Objetivo
            </a>
          ),
        },
      ],
    })

    const link = screen.getByRole('link', { name: 'Ver Objetivo' })
    expect(link).toHaveAttribute('href', '/learning/goals/goal-1')
    expect(link).toHaveClass('min-h-11')
    expect(screen.queryByRole('button')).toBeNull()
  })

  it('renders the picker slot between the destination and the actions', () => {
    renderCard({
      destination: 'Objetivo: Aprender a programar',
      actions: [{ key: 'decline', label: 'Recusar', variant: 'outline' }],
      children: <button type='button'>Trocar Objetivo</button>,
    })

    const card = screen.getByRole('region')
    const text = card.textContent ?? ''
    expect(within(card).getByRole('button', { name: 'Trocar Objetivo' })).toBeVisible()
    expect(text.indexOf('Objetivo: Aprender')).toBeLessThan(
      text.indexOf('Trocar Objetivo'),
    )
    expect(text.indexOf('Trocar Objetivo')).toBeLessThan(text.indexOf('Recusar'))
  })

  it.each([
    ['jade', 'bg-jade-tint'],
    ['danger', 'bg-danger/15'],
    ['muted', 'bg-muted'],
  ] as const)(
    'shows the %s icon box without relying on color alone',
    (tone, className) => {
      const { container } = renderCard({ icon: { name: 'trash-2', tone } })

      expect(container.querySelector(`.${CSS.escape(className)}`)).not.toBeNull()
      expect(screen.getByRole('heading', { level: 3 })).toBeVisible()
    },
  )
})
