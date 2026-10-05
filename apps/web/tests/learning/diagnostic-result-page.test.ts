import { LearningRouteIdsFaker } from '@/core/learning/fakers'
import { expect, navigateAuthenticatedPage, test } from '../playwright'

const ids = LearningRouteIdsFaker.fake()

function serverFnExport(url: string) {
  const id = new URL(url).pathname.split('/_serverFn/')[1] ?? ''
  try {
    return String(
      JSON.parse(Buffer.from(decodeURIComponent(id), 'base64').toString()).export ?? '',
    )
  } catch {
    return ''
  }
}

test('shows the authenticated consolidated diagnostic result without answer details', async ({
  authenticatedPage,
  bff,
}, testInfo) => {
  await bff.route(async (route) => {
    const exported = serverFnExport(route.request().url())

    if (exported.startsWith('getDiagnosticAction')) {
      await route.fulfill({
        body: JSON.stringify({
          result: {
            status: 'learning',
            runState: 'settled',
            readyToComplete: false,
            nextCompetencyId: ids.competencyId,
            nextActivityId: ids.activityId,
            pendingAttemptId: null,
            pendingAttemptStatus: null,
            focusCompetencyId: ids.competencyId,
            competencies: [
              {
                competencyId: ids.competencyId,
                competencyName: 'Estruturas de repetição',
                position: 1,
                progress: 65,
                coverageComplete: false,
                status: 'developing',
                isFocus: true,
                contentReleased: true,
              },
            ],
            initialRecommendation: {
              competencyId: ids.competencyId,
              competencyName: 'Estruturas de repetição',
              activityId: ids.activityId,
              activityTitle: 'Prática inicial',
              difficulty: 'easy',
              type: 'new-activity',
              reason: 'Retome a observação inicial.',
              targetConceptName: 'Laços básicos',
              materialId: null,
              gap: null,
            },
            initialOverallResult: 65,
            overallCoverageComplete: false,
            directCompletion: false,
          },
        }),
        contentType: 'application/json',
      })
      return
    }

    if (exported.startsWith('getSkillExperienceAction')) {
      await route.fulfill({
        body: JSON.stringify({
          result: {
            goalId: ids.goalId,
            skillId: ids.skillId,
            skillName: 'Lógica de programação',
            skillStatus: 'learning',
            overallResult: 65,
            overallCoverageComplete: false,
            focusCompetencyId: ids.competencyId,
            focusCompetencyName: 'Estruturas de repetição',
            competencies: [
              {
                competencyId: ids.competencyId,
                competencyName: 'Estruturas de repetição',
                position: 1,
                progress: 65,
                coverageComplete: false,
                status: 'developing',
                availability: 'available',
                isFocus: true,
              },
            ],
            recommendation: {
              competencyId: ids.competencyId,
              competencyName: 'Estruturas de repetição',
              activityId: ids.activityId,
              activityTitle: 'Somar os números pares',
              difficulty: 'medium',
              type: 'reinforcement',
              reason: 'Recomendação posterior mutável.',
              targetConceptName: 'Conteúdo posterior',
              materialId: null,
              gap: null,
            },
            recommendationGap: null,
            evaluation: null,
          },
        }),
        contentType: 'application/json',
      })
      return
    }

    await route.fallback()
  })

  await navigateAuthenticatedPage(
    authenticatedPage,
    `/learning/goals/${ids.goalId}/skills/${ids.skillId}/diagnostic/result`,
  )

  await expect(
    authenticatedPage.getByRole('heading', { level: 1, name: 'Seu ponto de partida' }),
  ).toBeVisible()
  await expect(authenticatedPage.getByText('65%', { exact: true }).first()).toBeVisible()
  await expect(
    authenticatedPage.getByRole('heading', {
      name: 'Ponto de partida por Competência (0–100)',
    }),
  ).toBeVisible()
  await expect(authenticatedPage.getByText('Retome a observação inicial.')).toBeVisible()
  await expect(
    authenticatedPage.getByText('Laços básicos', { exact: false }),
  ).toBeVisible()
  await expect(authenticatedPage.getByText(/posterior mutável/)).toHaveCount(0)
  await expect(
    authenticatedPage.getByText('Conteúdo posterior', { exact: false }),
  ).toHaveCount(0)
  await expect(authenticatedPage.getByText('Respostas individuais')).toHaveCount(0)
  const skillLink = authenticatedPage.getByRole('link', { name: 'Ver Habilidade' })
  await expect(skillLink).toHaveCount(1)
  await expect(skillLink).toHaveAttribute(
    'href',
    `/learning/goals/${ids.goalId}/skills/${ids.skillId}`,
  )
  await expect(
    authenticatedPage.getByRole('link', { name: 'Escolher outra' }),
  ).toHaveCount(0)
  await expect(
    authenticatedPage.getByRole('link', { name: 'Continuar praticando' }),
  ).toBeVisible()

  const recommendationSection = authenticatedPage
    .getByRole('heading', { name: 'Próximo passo recomendado' })
    .locator('..')
  await authenticatedPage.setViewportSize({ width: 1440, height: 900 })
  await recommendationSection.screenshot({
    path: testInfo.outputPath('diagnostic-result-desktop.png'),
  })
  await authenticatedPage.setViewportSize({ width: 390, height: 844 })
  await expect(skillLink).toBeVisible()
  await authenticatedPage.evaluate(() => window.scrollTo(0, document.body.scrollHeight))
  await recommendationSection.screenshot({
    path: testInfo.outputPath('diagnostic-result-mobile.png'),
  })

  await skillLink.click()
  await expect(authenticatedPage).toHaveURL(
    new RegExp(`/learning/goals/${ids.goalId}/skills/${ids.skillId}/?$`),
  )
  await expect(
    authenticatedPage.getByRole('heading', { level: 1, name: 'Lógica de programação' }),
  ).toBeVisible()
})
