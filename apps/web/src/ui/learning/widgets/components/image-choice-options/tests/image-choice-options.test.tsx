import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ImageChoiceOption } from '@/core/learning/choice-activity'

import { ImageChoiceOptions, type ImageChoiceOptionsProps } from '..'

const OPTIONS: readonly ImageChoiceOption[] = [
  {
    key: 'opt-1',
    imagePath: '/curriculum/images/2d165276ed215938.webp',
    description: 'Fatias brancas e firmes, sem brilho.',
  },
  {
    key: 'opt-2',
    imagePath: '/curriculum/images/51de9b1cc23dd653.webp',
    description: 'Fatias claras e translúcidas.',
  },
  {
    key: 'opt-3',
    imagePath: '/curriculum/images/5c8a6a6b47848a6f.webp',
    description: 'Tiras marrons e macias.',
  },
  {
    key: 'opt-4',
    imagePath: '/curriculum/images/655fecc77404ac40.webp',
    description: 'Fatias escuras com bordas pretas.',
  },
]

function renderOptions(overrides: Partial<ImageChoiceOptionsProps> = {}) {
  const props: ImageChoiceOptionsProps = {
    name: 'image-choice-q1',
    labelledBy: 'prompt-q1',
    options: OPTIONS,
    selectedOptionKey: null,
    state: 'selecting',
    ...overrides,
  }
  render(
    <>
      <h2 id='prompt-q1'>Qual destas cebolas está caramelizada?</h2>
      <ImageChoiceOptions {...props} />
    </>,
  )
}

describe('ImageChoiceOptions', () => {
  afterEach(cleanup)

  it('names every radio as its numbered option and links the description', () => {
    renderOptions()

    expect(
      screen.getByRole('radiogroup', { name: 'Qual destas cebolas está caramelizada?' }),
    ).toBeVisible()
    for (const [index, option] of OPTIONS.entries()) {
      expect(
        screen.getByRole('radio', { name: `Opção ${index + 1}` }),
      ).toHaveAccessibleDescription(option.description)
    }
  })

  it('renders the photos as decorative images from the curricular path', () => {
    renderOptions()

    const photos = document.querySelectorAll('img')
    expect(photos).toHaveLength(4)
    for (const [index, photo] of [...photos].entries()) {
      expect(photo).toHaveAttribute('alt', '')
      expect(photo).toHaveAttribute('src', OPTIONS[index].imagePath)
    }
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
  })

  it('selects by click, changes freely by arrow keys and reports each choice', async () => {
    const user = userEvent.setup()
    const onSelectOptionMock = vi.fn()
    renderOptions({ onSelectOption: onSelectOptionMock, selectedOptionKey: 'opt-1' })

    expect(screen.getByRole('radio', { name: 'Opção 1' })).toBeChecked()
    expect(screen.getByText('Selecionada')).toBeVisible()
    await user.click(screen.getByRole('radio', { name: 'Opção 3' }))
    expect(onSelectOptionMock).toHaveBeenLastCalledWith('opt-3')
    await user.keyboard('{ArrowRight}')
    expect(onSelectOptionMock).toHaveBeenLastCalledWith('opt-4')
  })

  it('locks every radio when the group is disabled while selecting', () => {
    renderOptions({ disabled: true, selectedOptionKey: 'opt-2' })

    for (const radio of screen.getAllByRole('radio')) expect(radio).toBeDisabled()
  })

  it('marks only the chosen image as wrong and dims the others after verifying', () => {
    renderOptions({ state: 'verified', selectedOptionKey: 'opt-4', isCorrect: false })

    const chosen = screen.getByRole('radio', { name: 'Opção 4' })
    expect(chosen).toBeChecked()
    expect(chosen).toBeDisabled()
    expect(chosen.closest('label')).toHaveAttribute('data-tone', 'incorrect')
    expect(
      within(chosen.closest('label') as HTMLElement).getByText('Sua resposta'),
    ).toBeVisible()
    for (const name of ['Opção 1', 'Opção 2', 'Opção 3']) {
      expect(screen.getByRole('radio', { name }).closest('label')).toHaveAttribute(
        'data-tone',
        'dimmed',
      )
    }
    expect(screen.queryByText('Resposta correta')).not.toBeInTheDocument()
    expect(screen.getAllByText('Sua resposta')).toHaveLength(1)
  })

  it('marks the chosen image as right after verifying a correct answer', () => {
    renderOptions({ state: 'verified', selectedOptionKey: 'opt-3', isCorrect: true })

    const chosen = screen.getByRole('radio', { name: 'Opção 3' }).closest('label')
    expect(chosen).toHaveAttribute('data-tone', 'correct')
    expect(within(chosen as HTMLElement).getByText('Sua resposta')).toBeVisible()
  })

  it('shows a read-only history that identifies no correct image without a disclosure', () => {
    renderOptions({ state: 'history', selectedOptionKey: 'opt-4', isCorrect: false })

    for (const radio of screen.getAllByRole('radio')) expect(radio).toBeDisabled()
    expect(screen.queryByText('Resposta correta')).not.toBeInTheDocument()
    expect(document.querySelectorAll('[data-tone="correct"]')).toHaveLength(0)
    expect(
      screen.getByRole('radio', { name: 'Opção 4' }).closest('label'),
    ).toHaveAttribute('data-tone', 'incorrect')
  })

  it('highlights the correct image in the history only when the server discloses it', () => {
    renderOptions({
      state: 'history',
      selectedOptionKey: 'opt-4',
      isCorrect: false,
      disclosedCorrectOptionKey: 'opt-3',
    })

    const correct = screen.getByRole('radio', { name: 'Opção 3' }).closest('label')
    expect(correct).toHaveAttribute('data-tone', 'correct')
    expect(within(correct as HTMLElement).getByText('Resposta correta')).toBeVisible()
    expect(
      screen.getByRole('radio', { name: 'Opção 4' }).closest('label'),
    ).toHaveAttribute('data-tone', 'incorrect')
    expect(
      screen.getByRole('radio', { name: 'Opção 1' }).closest('label'),
    ).toHaveAttribute('data-tone', 'dimmed')
  })

  it('never exposes a disclosed key while selecting', () => {
    renderOptions({ disclosedCorrectOptionKey: 'opt-3', selectedOptionKey: 'opt-1' })

    expect(document.querySelectorAll('[data-tone="correct"]')).toHaveLength(0)
    expect(screen.queryByText('Resposta correta')).not.toBeInTheDocument()
  })

  it('uses as many columns as options up to four', () => {
    renderOptions({ options: OPTIONS.slice(0, 3) })

    expect(
      screen.getByRole('radiogroup').style.getPropertyValue('--image-choice-columns'),
    ).toBe('3')
  })
})
