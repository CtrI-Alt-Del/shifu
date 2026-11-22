import type { ComponentProps } from 'react'

import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ROUTES } from '@/constants/routes'
import { useReducedMotionPreference } from '@/ui/shared/hooks/use-reduced-motion-preference'

import { SkillCompletion, type SkillCompletionProps } from '..'
import {
  type CompetencyRowView,
  type ComparisonView,
  useSkillCompletion,
} from '../use-skill-completion'

type LinkMockProps = Omit<ComponentProps<'a'>, 'href'> & {
  params?: Record<string, string>
  to: string
}

// Entrance motion and counters settle at once, so assertions see the final
// state; the shared components own their own animated cases.
vi.mock('@/ui/shared/hooks/use-reduced-motion-preference', () => ({
  useReducedMotionPreference: vi.fn(() => ({ prefersReducedMotion: true })),
}))
vi.mock('@tanstack/react-router', () => ({
  Link: ({ children, params, to, ...props }: LinkMockProps) => (
    <a data-params={JSON.stringify(params)} href={to} {...props}>
      {children}
    </a>
  ),
}))
vi.mock('../use-skill-completion', () => ({ useSkillCompletion: vi.fn() }))

const useSkillCompletionMock = vi.mocked(useSkillCompletion)
const useReducedMotionPreferenceMock = vi.mocked(useReducedMotionPreference)

const IDS = {
  goalId: '01SHF000000000000000000001',
  skillId: '01SHF000000000000000000002',
  firstCompetencyId: '01SHF000000000000000000003',
}

type SkillCompletionView = ReturnType<typeof useSkillCompletion>

const RISING: Pick<
  ComparisonView,
  'sign' | 'signLabel' | 'finalTone' | 'unknownPercent'
> = { sign: '→', signLabel: 'para', finalTone: 'rose', unknownPercent: 0 }

function row(
  index: number,
  name: string,
  initial: number,
  final: number,
  day: string,
  overrides: Partial<CompetencyRowView> = {},
): CompetencyRowView {
  const competencyId = `01SHF00000000000000000010${index}`
  return {
    ...RISING,
    competencyId,
    competencyName: name,
    initialText: `${initial}%`,
    finalText: `${final}%`,
    startingPercent: initial,
    gainPercent: final - initial,
    startingLabel: null,
    masteryText: `Dominada em ${day}`,
    accessibleName: `${name}. Dominada em ${day}. Inicial ${initial}%, final ${final}%.`,
    params: { goalId: IDS.goalId, skillId: IDS.skillId, competencyId },
    ...overrides,
  }
}

const EVOLUTION_VIEW: SkillCompletionView = {
  skillName: 'Lógica de programação',
  statusLabel: 'Concluída',
  dateRange: '2 set → 13 set',
  dateRangeLabel: 'De 2 set a 13 set',
  intro:
    'Compare o ponto de partida com o resultado final. A prática continua liberada, mas novas notas não alteram este resumo.',
  kind: 'evolution',
  indicators: [
    {
      id: 'duration',
      label: 'Do início à conclusão',
      value: 11,
      format: (v) => `${v} dias`,
    },
    {
      id: 'activities',
      label: 'Atividades de aprendizagem feitas',
      value: 14,
      format: (v) => String(v),
    },
    {
      id: 'attempts',
      label: 'Tentativas enviadas até a conclusão',
      value: 22,
      format: (v) => String(v),
    },
  ],
  legendItems: [
    { id: 'start', label: 'Ponto de partida', tone: 'start' },
    { id: 'evolution', label: 'Evolução até agora', tone: 'evolution' },
  ],
  overall: {
    ...RISING,
    label: 'Resultado geral da Habilidade',
    initialText: '64%',
    finalText: '91%',
    startingPercent: 64,
    gainPercent: 27,
    startingLabel: null,
  },
  competencies: [
    row(1, 'Variáveis e tipos', 92, 96, '4 set'),
    row(2, 'Condicionais', 88, 93, '6 set'),
    row(3, 'Estruturas de repetição', 46, 89, '10 set'),
    row(4, 'Funções', 30, 86, '13 set'),
  ],
  review: {
    title: 'Prática de revisão',
    notice:
      'Notas de revisão ficam no histórico e não alteram o resultado oficial desta Habilidade.',
    stats: [
      { id: 'attempts', value: 3, label: 'tentativas de revisão' },
      { id: 'latest-score', value: 85, label: 'última nota de revisão' },
    ],
  },
  goalParams: { goalId: IDS.goalId },
}

const DIAGNOSIS_VIEW: SkillCompletionView = {
  ...EVOLUTION_VIEW,
  dateRange: '2 set → 2 set',
  dateRangeLabel: 'De 2 set a 2 set',
  intro:
    'Você concluiu esta Habilidade no diagnóstico, por isso o ponto de partida e o resultado final são iguais. A prática continua liberada, mas novas notas não alteram este resumo.',
  kind: 'diagnosis',
  indicators: [
    {
      id: 'duration',
      label: 'Do início à conclusão',
      value: 0,
      format: () => 'No mesmo dia',
    },
  ],
  legendItems: [
    { id: 'start', label: 'Ponto de partida = resultado final', tone: 'start' },
  ],
  overall: {
    ...EVOLUTION_VIEW.overall,
    initialText: '90%',
    finalText: '90%',
    sign: '=',
    signLabel: 'igual a',
    finalTone: 'neutral',
    startingPercent: 90,
    gainPercent: 0,
  },
  competencies: [
    row(1, 'Variáveis e tipos', 92, 92, '2 set', {
      sign: '=',
      signLabel: 'igual a',
      finalTone: 'neutral',
      gainPercent: 0,
      accessibleName: 'Variáveis e tipos. Dominada em 2 set. Inicial e final 92%.',
    }),
  ],
  review: {
    title: 'Prática de revisão',
    notice:
      'Você ainda não fez revisões. A prática continua disponível, e as notas de revisão não alteram o resultado oficial desta Habilidade.',
    stats: [],
  },
}

const PARTIAL_VIEW: SkillCompletionView = {
  ...EVOLUTION_VIEW,
  intro:
    'Compare o ponto de partida com o resultado final. O diagnóstico não observou todas as dificuldades, então parte do ponto de partida é parcial ou desconhecida. A prática continua liberada, mas novas notas não alteram este resumo.',
  kind: 'partial',
  legendItems: [
    ...EVOLUTION_VIEW.legendItems,
    { id: 'unknown', label: 'Resultado sem ponto de partida', tone: 'unknown' },
  ],
  overall: {
    ...EVOLUTION_VIEW.overall,
    initialText: '75%',
    startingPercent: 75,
    gainPercent: 16,
    startingLabel: 'Ponto de partida parcial',
  },
  competencies: [
    row(3, 'Estruturas de repetição', 46, 89, '10 set', {
      startingLabel: 'Ponto de partida parcial',
      accessibleName:
        'Estruturas de repetição. Ponto de partida parcial. Dominada em 10 set. Inicial 46%, final 89%.',
    }),
    row(4, 'Funções', 0, 86, '13 set', {
      initialText: '—',
      finalTone: 'neutral',
      startingPercent: 0,
      gainPercent: 0,
      unknownPercent: 86,
      startingLabel: 'Ponto de partida desconhecido',
      accessibleName:
        'Funções. Ponto de partida desconhecido. Dominada em 13 set. Inicial desconhecido, final 86%.',
    }),
  ],
}

function renderCompletion(
  view: SkillCompletionView,
  props: Partial<SkillCompletionProps> = {},
) {
  useSkillCompletionMock.mockReturnValue(view)
  const onRemove = vi.fn()
  render(
    <SkillCompletion
      completion={{} as SkillCompletionProps['completion']}
      goalId={IDS.goalId}
      onRemove={onRemove}
      skillId={IDS.skillId}
      skillName='Lógica de programação'
      {...props}
    />,
  )
  return { onRemove }
}

describe('SkillCompletion', () => {
  beforeEach(() => {
    useSkillCompletionMock.mockReset()
    useReducedMotionPreferenceMock.mockReturnValue({ prefersReducedMotion: true })
  })
  afterEach(cleanup)

  it('renders the evolution state with the header, indicators, legend, overall result and review', () => {
    renderCompletion(EVOLUTION_VIEW)

    expect(
      screen.getByRole('heading', { level: 1, name: 'Lógica de programação' }),
    ).toBeVisible()
    expect(screen.getByText('Concluída')).toBeVisible()
    expect(screen.getByText('2 set → 13 set')).toBeInTheDocument()
    expect(screen.getByText('De 2 set a 13 set')).toBeInTheDocument()
    expect(screen.getByText(EVOLUTION_VIEW.intro)).toBeVisible()

    const indicators = screen.getByRole('list', { name: 'Indicadores da Habilidade' })
    expect(within(indicators).getAllByRole('listitem')).toHaveLength(3)
    expect(within(indicators).getByText('11 dias')).toBeVisible()
    expect(within(indicators).getByText('Do início à conclusão')).toBeVisible()
    expect(within(indicators).getByText('14')).toBeVisible()
    expect(
      within(indicators).getByText('Atividades de aprendizagem feitas'),
    ).toBeVisible()
    expect(within(indicators).getByText('22')).toBeVisible()
    expect(
      within(indicators).getByText('Tentativas enviadas até a conclusão'),
    ).toBeVisible()

    const legend = screen.getByRole('list', { name: 'Legenda da comparação' })
    expect(
      within(legend)
        .getAllByRole('listitem')
        .map((item) => item.textContent),
    ).toEqual(['Ponto de partida', 'Evolução até agora'])

    const overall = screen.getByRole('region', { name: 'Resultado geral da Habilidade' })
    expect(within(overall).getByText('64%')).toBeVisible()
    expect(within(overall).getByText('→')).toBeInTheDocument()
    expect(within(overall).getByText('91%')).toHaveClass('text-jade-text')

    const review = screen.getByRole('region', { name: 'Prática de revisão' })
    expect(within(review).getByText(EVOLUTION_VIEW.review.notice)).toBeVisible()
    expect(within(review).getByText('3')).toBeVisible()
    expect(within(review).getByText('tentativas de revisão')).toBeVisible()
    expect(within(review).getByText('85')).toBeVisible()
    expect(within(review).getByText('última nota de revisão')).toBeVisible()
  })

  it('renders every Competency as a link to its Competency page with a full accessible name', () => {
    renderCompletion(EVOLUTION_VIEW)

    const list = screen.getByRole('region', { name: 'Competências desta Habilidade' })
    const links = within(list).getAllByRole('link')
    expect(links.map((link) => link.getAttribute('aria-label'))).toEqual([
      'Variáveis e tipos. Dominada em 4 set. Inicial 92%, final 96%.',
      'Condicionais. Dominada em 6 set. Inicial 88%, final 93%.',
      'Estruturas de repetição. Dominada em 10 set. Inicial 46%, final 89%.',
      'Funções. Dominada em 13 set. Inicial 30%, final 86%.',
    ])
    for (const link of links) {
      expect(link).toHaveAttribute('href', ROUTES.learningCompetency)
    }
    expect(
      JSON.parse(
        within(list)
          .getByRole('link', { name: /^Variáveis e tipos/ })
          .getAttribute('data-params') ?? '{}',
      ),
    ).toEqual({
      goalId: IDS.goalId,
      skillId: IDS.skillId,
      competencyId: '01SHF000000000000000000101',
    })
    const firstRow = within(list).getByRole('link', {
      name: 'Variáveis e tipos. Dominada em 4 set. Inicial 92%, final 96%.',
    })
    expect(firstRow).toHaveTextContent('Variáveis e tipos')
    expect(firstRow).toHaveTextContent('Dominada em 4 set')
    expect(firstRow).toHaveTextContent('92%')
    expect(firstRow).toHaveTextContent('96%')
  })

  it('links "Voltar ao Objetivo" to the Goal', () => {
    renderCompletion(EVOLUTION_VIEW)

    const link = screen.getByRole('link', { name: 'Voltar ao Objetivo' })
    expect(link).toHaveAttribute('href', ROUTES.learningGoal)
    expect(JSON.parse(link.getAttribute('data-params') ?? '{}')).toEqual({
      goalId: IDS.goalId,
    })
  })

  it('renders the diagnosis state with a single duration card, equal values and no numbers in the review', () => {
    renderCompletion(DIAGNOSIS_VIEW)

    expect(screen.getByText('2 set → 2 set')).toBeInTheDocument()
    expect(screen.getByText(DIAGNOSIS_VIEW.intro)).toBeVisible()
    const indicators = screen.getByRole('list', { name: 'Indicadores da Habilidade' })
    expect(within(indicators).getAllByRole('listitem')).toHaveLength(1)
    expect(within(indicators).getByText('No mesmo dia')).toBeVisible()
    expect(
      screen.queryByText('Atividades de aprendizagem feitas'),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByText('Tentativas enviadas até a conclusão'),
    ).not.toBeInTheDocument()

    const legend = screen.getByRole('list', { name: 'Legenda da comparação' })
    expect(within(legend).getAllByRole('listitem')).toHaveLength(1)
    expect(within(legend).getByText('Ponto de partida = resultado final')).toBeVisible()

    const overall = screen.getByRole('region', { name: 'Resultado geral da Habilidade' })
    expect(within(overall).getByText('=')).toBeInTheDocument()
    expect(within(overall).getAllByText('90%')).toHaveLength(2)
    expect(within(overall).queryByText('→')).not.toBeInTheDocument()
    expect(
      within(overall).queryByText('Ponto de partida parcial'),
    ).not.toBeInTheDocument()

    const review = screen.getByRole('region', { name: 'Prática de revisão' })
    expect(within(review).getByText(DIAGNOSIS_VIEW.review.notice)).toBeVisible()
    expect(within(review).queryByRole('list')).not.toBeInTheDocument()
    expect(within(review).queryByText('tentativas de revisão')).not.toBeInTheDocument()
  })

  it('renders the partial state with the partial and unknown labels and the third legend item', () => {
    renderCompletion(PARTIAL_VIEW)

    expect(screen.getByText(PARTIAL_VIEW.intro)).toBeVisible()
    const legend = screen.getByRole('list', { name: 'Legenda da comparação' })
    expect(
      within(legend)
        .getAllByRole('listitem')
        .map((item) => item.textContent),
    ).toEqual([
      'Ponto de partida',
      'Evolução até agora',
      'Resultado sem ponto de partida',
    ])

    const overall = screen.getByRole('region', { name: 'Resultado geral da Habilidade' })
    expect(within(overall).getByText('Ponto de partida parcial')).toBeVisible()
    expect(within(overall).getByText('75%')).toBeVisible()

    const partialRow = screen.getByRole('link', { name: /^Estruturas de repetição/ })
    expect(partialRow).toHaveTextContent('Ponto de partida parcial')
    expect(partialRow).toHaveTextContent('46%')

    const unknownRow = screen.getByRole('link', { name: /^Funções/ })
    expect(unknownRow).toHaveTextContent('Ponto de partida desconhecido')
    expect(unknownRow).toHaveTextContent('—')
    expect(unknownRow).toHaveTextContent('86%')
    expect(unknownRow).toHaveAccessibleName(
      'Funções. Ponto de partida desconhecido. Dominada em 13 set. Inicial desconhecido, final 86%.',
    )
  })

  it('shows the review block without a score when no review evaluation finished', () => {
    renderCompletion({
      ...EVOLUTION_VIEW,
      review: {
        ...EVOLUTION_VIEW.review,
        stats: [{ id: 'attempts', value: 1, label: 'tentativa de revisão' }],
      },
    })

    const review = screen.getByRole('region', { name: 'Prática de revisão' })
    expect(within(review).getByText('1')).toBeVisible()
    expect(within(review).getByText('tentativa de revisão')).toBeVisible()
    expect(within(review).queryByText('última nota de revisão')).not.toBeInTheDocument()
  })

  it('reaches the actions menu, each Competency row and the back link by keyboard in reading order', async () => {
    const user = userEvent.setup()
    renderCompletion(EVOLUTION_VIEW)

    await user.tab()
    expect(
      screen.getByRole('button', { name: 'Mais ações de Lógica de programação' }),
    ).toHaveFocus()
    await user.tab()
    expect(screen.getByRole('link', { name: /^Variáveis e tipos/ })).toHaveFocus()
    await user.tab()
    expect(screen.getByRole('link', { name: /^Condicionais/ })).toHaveFocus()
    await user.tab()
    await user.tab()
    expect(screen.getByRole('link', { name: /^Funções/ })).toHaveFocus()
    await user.tab()
    expect(screen.getByRole('link', { name: 'Voltar ao Objetivo' })).toHaveFocus()
  })

  it('opens the Skill removal from the shared actions menu', async () => {
    const user = userEvent.setup()
    const { onRemove } = renderCompletion(EVOLUTION_VIEW)

    await user.click(
      screen.getByRole('button', { name: 'Mais ações de Lógica de programação' }),
    )
    await user.click(screen.getByRole('menuitem', { name: 'Remover habilidade' }))

    expect(onRemove).toHaveBeenCalledOnce()
  })

  it('shows the final figures on first render under reduced motion', () => {
    renderCompletion(EVOLUTION_VIEW)

    expect(screen.getByText('11 dias')).toBeVisible()
    expect(screen.getByText('85')).toBeVisible()
  })
})
