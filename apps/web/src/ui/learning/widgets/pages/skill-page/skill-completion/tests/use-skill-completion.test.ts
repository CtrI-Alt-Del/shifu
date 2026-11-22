import { renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { SkillExperienceDetailFaker } from '@/core/learning/fakers'
import type { SkillCompletionOverview } from '@/core/learning/skill-experience'

import type { SkillCompletionProps } from '..'
import { useSkillCompletion } from '../use-skill-completion'

const IDS = {
  goalId: '01SHF000000000000000000001',
  skillId: '01SHF000000000000000000002',
}

function render(overrides: Partial<SkillCompletionOverview> = {}) {
  const completion = SkillExperienceDetailFaker.fakeCompletion(overrides)
  const props: SkillCompletionProps = {
    goalId: IDS.goalId,
    skillId: IDS.skillId,
    skillName: 'Lógica de programação',
    completion,
    onRemove: () => {},
  }
  const { result } = renderHook(() => useSkillCompletion(props))

  return { completion, view: result.current }
}

describe('useSkillCompletion', () => {
  it('prepares the evolution state with the date range, intro and legend', () => {
    const { view } = render()

    expect(view.kind).toBe('evolution')
    expect(view.skillName).toBe('Lógica de programação')
    expect(view.statusLabel).toBe('Concluída')
    expect(view.dateRange).toBe('2 set → 13 set')
    expect(view.dateRangeLabel).toBe('De 2 set a 13 set')
    expect(view.intro).toBe(
      'Compare o ponto de partida com o resultado final. A prática continua liberada, mas novas notas não alteram este resumo.',
    )
    expect(view.legendItems).toEqual([
      { id: 'start', label: 'Ponto de partida', tone: 'start' },
      { id: 'evolution', label: 'Evolução até agora', tone: 'evolution' },
    ])
    expect(view.goalParams).toEqual({ goalId: IDS.goalId })
  })

  it('shows the three indicators with their labels and final values', () => {
    const { view } = render()

    expect(view.indicators.map((indicator) => indicator.id)).toEqual([
      'duration',
      'activities',
      'attempts',
    ])
    expect(view.indicators.map((indicator) => indicator.label)).toEqual([
      'Do início à conclusão',
      'Atividades de aprendizagem feitas',
      'Tentativas enviadas até a conclusão',
    ])
    expect(view.indicators.map((indicator) => indicator.format(indicator.value))).toEqual(
      ['11 dias', '14', '22'],
    )
  })

  it.each([
    [0, 'No mesmo dia'],
    [1, '1 dia'],
    [11, '11 dias'],
  ])('writes a duration of %i days as "%s"', (durationDays, text) => {
    const { view } = render({ durationDays })
    const [duration] = view.indicators

    expect(duration?.value).toBe(durationDays)
    expect(duration?.format(durationDays)).toBe(text)
  })

  it('keeps the same-day text while the counter passes through other figures', () => {
    const { view } = render({ durationDays: 0 })

    expect(view.indicators[0]?.format(0)).toBe('No mesmo dia')
  })

  it('hides the two counts when the diagnosis completed the Skill', () => {
    const { view } = render({
      completedByDiagnosis: true,
      durationDays: 0,
      learningActivityCount: null,
      learningAttemptCount: null,
    })

    expect(view.indicators.map((indicator) => indicator.id)).toEqual(['duration'])
  })

  it('omits a count the server did not provide', () => {
    const { view } = render({ learningActivityCount: null })

    expect(view.indicators.map((indicator) => indicator.id)).toEqual([
      'duration',
      'attempts',
    ])
  })

  it('compares each Competency in curriculum order with its gain and tone', () => {
    const { view } = render()
    const [first, second, third, fourth] = view.competencies

    expect(view.competencies.map((row) => row.competencyName)).toEqual([
      'Variáveis e tipos',
      'Condicionais',
      'Estruturas de repetição',
      'Funções',
    ])
    expect(first).toMatchObject({
      initialText: '92%',
      finalText: '96%',
      sign: '→',
      signLabel: 'para',
      finalTone: 'rose',
      startingPercent: 92,
      gainPercent: 4,
      unknownPercent: 0,
      startingLabel: null,
      masteryText: 'Dominada em 4 set',
    })
    expect(second?.masteryText).toBe('Dominada em 6 set')
    expect(third).toMatchObject({ startingPercent: 46, gainPercent: 43 })
    expect(fourth?.masteryText).toBe('Dominada em 13 set')
  })

  it('orders Competencies by position even when the server sends them shuffled', () => {
    const base = SkillExperienceDetailFaker.fakeCompletion()
    const { view } = render({ competencies: [...base.competencies].reverse() })

    expect(view.competencies.map((row) => row.competencyName)).toEqual([
      'Variáveis e tipos',
      'Condicionais',
      'Estruturas de repetição',
      'Funções',
    ])
  })

  it('builds each row link params and an accessible name with name, both values and mastery day', () => {
    const { view, completion } = render()
    const [first] = view.competencies

    expect(first?.params).toEqual({
      goalId: IDS.goalId,
      skillId: IDS.skillId,
      competencyId: completion.competencies[0]?.competencyId,
    })
    expect(first?.accessibleName).toBe(
      'Variáveis e tipos. Dominada em 4 set. Inicial 92%, final 96%.',
    )
  })

  it('compares the overall result like a row', () => {
    const { view } = render()

    expect(view.overall).toMatchObject({
      label: 'Resultado geral da Habilidade',
      initialText: '64%',
      finalText: '91%',
      sign: '→',
      finalTone: 'rose',
      startingPercent: 64,
      gainPercent: 27,
      startingLabel: null,
    })
  })

  it('shows equal values and no evolution when the diagnosis completed the Skill', () => {
    const { view } = render({
      completedByDiagnosis: true,
      durationDays: 0,
      startedOn: '2026-09-02',
      completedOn: '2026-09-02',
      learningActivityCount: null,
      learningAttemptCount: null,
      initialResult: 90,
      finalResult: 90,
      competencies: SkillExperienceDetailFaker.fakeCompletion().competencies.map(
        (competency) => ({
          ...competency,
          initialProgress: competency.finalProgress,
          masteredOn: '2026-09-02',
        }),
      ),
    })

    expect(view.kind).toBe('diagnosis')
    expect(view.dateRange).toBe('2 set → 2 set')
    expect(view.intro).toBe(
      'Você concluiu esta Habilidade no diagnóstico, por isso o ponto de partida e o resultado final são iguais. A prática continua liberada, mas novas notas não alteram este resumo.',
    )
    expect(view.legendItems).toEqual([
      { id: 'start', label: 'Ponto de partida = resultado final', tone: 'start' },
    ])
    expect(view.overall).toMatchObject({
      initialText: '90%',
      finalText: '90%',
      sign: '=',
      signLabel: 'igual a',
      finalTone: 'neutral',
      startingPercent: 90,
      gainPercent: 0,
    })
    for (const row of view.competencies) {
      expect(row).toMatchObject({
        sign: '=',
        finalTone: 'neutral',
        gainPercent: 0,
        startingLabel: null,
        masteryText: 'Dominada em 2 set',
      })
      expect(row.initialText).toBe(row.finalText)
    }
    expect(view.competencies[0]?.accessibleName).toBe(
      'Variáveis e tipos. Dominada em 2 set. Inicial e final 96%.',
    )
  })

  it('labels partial and unknown starting points and keeps the invented number out', () => {
    const base = SkillExperienceDetailFaker.fakeCompletion()
    const [first, second, third, fourth] = base.competencies
    if (!first || !second || !third || !fourth)
      throw new Error('Expected four Competencies')
    const { view } = render({
      initialResult: 75,
      initialResultCoverage: 'partial',
      competencies: [
        first,
        second,
        { ...third, initialCoverage: 'partial' },
        { ...fourth, initialProgress: null, initialCoverage: 'unknown' },
      ],
    })

    expect(view.kind).toBe('partial')
    expect(view.intro).toContain('O diagnóstico não observou todas as dificuldades')
    expect(view.legendItems.map((item) => item.label)).toEqual([
      'Ponto de partida',
      'Evolução até agora',
      'Resultado sem ponto de partida',
    ])
    expect(view.legendItems[2]?.tone).toBe('unknown')
    expect(view.overall.startingLabel).toBe('Ponto de partida parcial')
    expect(view.competencies.map((row) => row.startingLabel)).toEqual([
      null,
      null,
      'Ponto de partida parcial',
      'Ponto de partida desconhecido',
    ])
    expect(view.competencies[2]).toMatchObject({
      initialText: '46%',
      startingPercent: 46,
      gainPercent: 43,
    })
    expect(view.competencies[3]).toMatchObject({
      initialText: '—',
      finalText: '86%',
      finalTone: 'neutral',
      startingPercent: 0,
      gainPercent: 0,
      unknownPercent: 86,
    })
    expect(view.competencies[3]?.accessibleName).toBe(
      'Funções. Ponto de partida desconhecido. Dominada em 13 set. Inicial desconhecido, final 86%.',
    )
  })

  it('labels the overall result unknown when no Competency start is known', () => {
    const { view } = render({ initialResult: null, initialResultCoverage: 'unknown' })

    expect(view.kind).toBe('partial')
    expect(view.overall).toMatchObject({
      initialText: '—',
      startingLabel: 'Ponto de partida desconhecido',
      unknownPercent: 91,
    })
  })

  it('shows the review counts and the latest score when review attempts exist', () => {
    const { view } = render({ review: { attemptCount: 3, latestScore: 85 } })

    expect(view.review).toEqual({
      title: 'Prática de revisão',
      notice:
        'Notas de revisão ficam no histórico e não alteram o resultado oficial desta Habilidade.',
      stats: [
        { id: 'attempts', value: 3, label: 'tentativas de revisão' },
        { id: 'latest-score', value: 85, label: 'última nota de revisão' },
      ],
    })
  })

  it('omits the review score when no review evaluation finished and singularizes one attempt', () => {
    const { view } = render({ review: { attemptCount: 1, latestScore: null } })

    expect(view.review.stats).toEqual([
      { id: 'attempts', value: 1, label: 'tentativa de revisão' },
    ])
  })

  it('says practice remains available and shows no numbers without review attempts', () => {
    const { view } = render({ review: { attemptCount: 0, latestScore: null } })

    expect(view.review.stats).toEqual([])
    expect(view.review.notice).toBe(
      'Você ainda não fez revisões. A prática continua disponível, e as notas de revisão não alteram o resultado oficial desta Habilidade.',
    )
  })
})
