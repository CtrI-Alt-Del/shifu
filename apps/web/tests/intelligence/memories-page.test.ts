import type { Locator, Page } from '@playwright/test'

import { ROUTES } from '../../src/constants/routes'
import { expect, test } from '../playwright'
import {
  CATEGORY_LABELS,
  expectNoHorizontalOverflow,
  installMentorMemoriesBackend,
  MEMORY_IDS,
  MESSAGE_IDS,
  openMemoriesPage,
  searchOf,
  SESSION_ID,
  SESSION_TITLE,
} from '../support/mentor-memories-backend'

// Browser integration with mocked transport: it proves the UI-to-BFF contract and the
// rendered states of the Memórias page, not real authentication or persistence.

const DESKTOP = { width: 1440, height: 900 }
const MOBILE = { width: 390, height: 844 }

function rows(page: Page): Locator {
  return page.getByRole('list', { name: 'Lista de memórias' }).getByRole('button')
}

function mapNodes(page: Page): Locator {
  return page
    .getByRole('region', { name: 'Mapa de memórias' })
    .locator('button[aria-pressed]')
}

function details(page: Page): Locator {
  return page.getByRole('region', { name: 'Detalhes da memória' })
}

function searchbox(page: Page): Locator {
  return page.getByRole('searchbox', { name: 'Buscar memórias' })
}

async function selectRow(page: Page, content: string) {
  await rows(page).filter({ hasText: content }).click()
}

test.describe('MemoriesPage', () => {
  test('redirects anonymous visitors to the login page', async ({ page }) => {
    await page.goto('/intelligence/memories/')

    await expect(page).toHaveURL(/\/login\/?$/)
    await expect(page.getByRole('heading', { level: 1, name: 'Memórias' })).toHaveCount(0)
  })

  test('renders the list with the header, the way back and the unfiltered request', async ({
    authenticatedPage: page,
  }) => {
    await page.setViewportSize(DESKTOP)
    const backend = await installMentorMemoriesBackend(page)

    await openMemoriesPage(page)

    await expect(page).toHaveURL(/\/intelligence\/memories\/?(\?.*)?$/)
    expect(searchOf(page).get('view') ?? 'list').toBe('list')
    await expect(
      page.getByText('O que o Mentor lembra para adaptar as explicações a você.'),
    ).toBeVisible()
    await expect(page.getByRole('link', { name: 'Voltar ao Mentor' })).toHaveAttribute(
      'href',
      ROUTES.intelligence,
    )
    await expect(rows(page)).toHaveCount(8)
    await expect(rows(page).first()).toContainText('Agora prefiro exemplos em Python.')
    await expect(rows(page).first()).toContainText(CATEGORY_LABELS.explanation_preference)
    await expect(page.getByRole('button', { name: 'Todas · 8' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    const [request] = backend.callsOf('list')
    expect(request?.method).toBe('GET')
    expect(request?.data).toMatchObject({ accountEmail: 'playwright@shifu.local' })
    expect(request?.data.q).toBeUndefined()
    expect(request?.data.category).toBeUndefined()
    await expect(details(page)).toHaveCount(0)
  })

  test('reaches the request and the visible state with the initial search values', async ({
    authenticatedPage: page,
  }) => {
    await page.setViewportSize(DESKTOP)
    const backend = await installMentorMemoriesBackend(page)

    await openMemoriesPage(page, {
      q: 'python',
      category: 'declared_knowledge',
      view: 'map',
      memory: MEMORY_IDS.knowledge,
    })

    await expect(searchbox(page)).toHaveValue('python')
    await expect(
      page.getByRole('button', { name: 'Conhecimento declarado', exact: true }),
    ).toHaveAttribute('aria-pressed', 'true')
    await expect(page.getByRole('tab', { name: 'Mapa' })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    await expect(mapNodes(page)).toHaveCount(1)
    await expect(
      details(page).getByRole('heading', {
        level: 2,
        name: 'Conheço variáveis e condicionais em Python.',
      }),
    ).toBeVisible()
    const [request] = backend.callsOf('list')
    expect(request?.data).toMatchObject({ q: 'python', category: 'declared_knowledge' })
    expect(backend.callsOf('get')).toHaveLength(0)
    expect(searchOf(page).get('memory')).toBe(MEMORY_IDS.knowledge)
  })

  test('drops invalid search values deterministically', async ({
    authenticatedPage: page,
  }) => {
    await page.setViewportSize(DESKTOP)
    const backend = await installMentorMemoriesBackend(page)

    await openMemoriesPage(page, {
      q: 'x'.repeat(101),
      category: 'bogus',
      view: 'grid',
      memory: 'not-a-ulid',
    })

    await expect(rows(page)).toHaveCount(8)
    await expect(searchbox(page)).toHaveValue('')
    await expect(page.getByRole('tab', { name: 'Lista' })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    const search = searchOf(page)
    expect(search.get('q')).toBeNull()
    expect(search.get('category')).toBeNull()
    expect(search.get('memory')).toBeNull()
    expect(search.get('view') ?? 'list').toBe('list')
    expect(backend.callsOf('list')[0]?.data.q).toBeUndefined()
    expect(backend.callsOf('list')[0]?.data.category).toBeUndefined()
    await expect(details(page)).toHaveCount(0)
  })

  test('keeps the URL, the request and the list in step with search, category and view changes', async ({
    authenticatedPage: page,
  }) => {
    await page.setViewportSize(DESKTOP)
    const backend = await installMentorMemoriesBackend(page)
    await openMemoriesPage(page)

    await searchbox(page).fill('python')
    await expect.poll(() => searchOf(page).get('q')).toBe('python')
    await expect(rows(page)).toHaveCount(2)
    expect(backend.callsOf('list').at(-1)?.data).toMatchObject({ q: 'python' })

    await page
      .getByRole('button', { name: 'Preferência de explicação', exact: true })
      .click()
    await expect.poll(() => searchOf(page).get('category')).toBe('explanation_preference')
    await expect(rows(page)).toHaveCount(1)
    await expect(
      page.getByRole('button', { name: 'Todas', exact: true }),
    ).toHaveAttribute('aria-pressed', 'false')
    expect(backend.callsOf('list').at(-1)?.data).toMatchObject({
      q: 'python',
      category: 'explanation_preference',
    })

    await page.getByRole('tab', { name: 'Mapa' }).click()
    await expect.poll(() => searchOf(page).get('view')).toBe('map')
    await expect(mapNodes(page)).toHaveCount(1)
    await expect(rows(page)).toHaveCount(0)

    await page.getByRole('button', { name: 'Todas', exact: true }).click()
    await expect.poll(() => searchOf(page).get('category')).toBeNull()
    await searchbox(page).fill('')
    await expect.poll(() => searchOf(page).get('q')).toBeNull()
    await expect(mapNodes(page)).toHaveCount(8)
    await page.getByRole('tab', { name: 'Lista' }).click()
    await expect(rows(page)).toHaveCount(8)
  })

  test('shows the loading skeleton until the memories arrive', async ({
    authenticatedPage: page,
  }) => {
    await page.setViewportSize(DESKTOP)
    const backend = await installMentorMemoriesBackend(page)
    const release = backend.holdList()

    await openMemoriesPage(page)

    await expect(
      page.getByRole('status').filter({ hasText: 'Carregando memórias.' }),
    ).toBeAttached()
    await expect(rows(page)).toHaveCount(0)
    await expect(searchbox(page)).toBeEnabled()
    release()
    await expect(rows(page)).toHaveCount(8)
  })

  test('shows the busy state instead of the previous results while a new filter is read', async ({
    authenticatedPage: page,
  }) => {
    await page.setViewportSize(DESKTOP)
    const backend = await installMentorMemoriesBackend(page)
    await openMemoriesPage(page)
    await expect(rows(page)).toHaveCount(8)
    const release = backend.holdList()

    await searchbox(page).fill('python')

    await expect(
      page.getByRole('status').filter({ hasText: 'Carregando memórias.' }),
    ).toBeAttached()
    await expect(rows(page)).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Todas', exact: true })).toBeVisible()
    expect(searchOf(page).get('q')).toBe('python')
    release()

    await expect(rows(page)).toHaveCount(2)
    await expect(
      page.getByRole('status').filter({ hasText: 'Carregando memórias.' }),
    ).toHaveCount(0)
  })

  test('explains an account without memories', async ({ authenticatedPage: page }) => {
    await page.setViewportSize(DESKTOP)
    await installMentorMemoriesBackend(page, [])

    await openMemoriesPage(page)

    await expect(
      page.getByRole('heading', { name: 'Você ainda não tem memórias' }),
    ).toBeVisible()
    await expect(page.getByRole('button', { name: 'Limpar filtros' })).toHaveCount(0)
  })

  test('explains an empty filtered result and clears the filters', async ({
    authenticatedPage: page,
  }) => {
    await page.setViewportSize(DESKTOP)
    await installMentorMemoriesBackend(page)

    await openMemoriesPage(page, { q: 'inexistente' })

    await expect(
      page.getByRole('heading', { name: 'Nenhuma memória encontrada' }),
    ).toBeVisible()
    await page.getByRole('button', { name: 'Limpar filtros' }).click()

    await expect(rows(page)).toHaveCount(8)
    await expect(searchbox(page)).toHaveValue('')
    expect(searchOf(page).get('q')).toBeNull()
  })

  test('shows a recoverable error and recovers on retry', async ({
    authenticatedPage: page,
  }) => {
    await page.setViewportSize(DESKTOP)
    const backend = await installMentorMemoriesBackend(page)
    backend.failNext('list')

    await openMemoriesPage(page)

    await expect(page.getByRole('alert')).toContainText(
      'Não foi possível carregar suas memórias',
    )
    await page.getByRole('button', { name: 'Tentar novamente' }).click()

    await expect(rows(page)).toHaveCount(8)
    expect(backend.callsOf('list')).toHaveLength(2)
  })

  test('selects a memory and shows its origins, concepts and the proficiency note', async ({
    authenticatedPage: page,
  }) => {
    await page.setViewportSize(DESKTOP)
    await installMentorMemoriesBackend(page)
    await openMemoriesPage(page)

    await selectRow(page, 'Confundo exibir e retornar valores.')

    await expect.poll(() => searchOf(page).get('memory')).toBe(MEMORY_IDS.difficulty)
    await expect(details(page).getByText('Dificuldade recorrente')).toBeVisible()
    await expect(
      details(page).getByRole('link', { name: SESSION_TITLE }),
    ).toHaveAttribute(
      'href',
      new RegExp(
        `/intelligence/?\\?(session=${SESSION_ID}&message=${MESSAGE_IDS.firstQuestion}|message=${MESSAGE_IDS.firstQuestion}&session=${SESSION_ID})`,
      ),
    )
    await expect(details(page).getByText('Conversa excluída')).toBeVisible()
    await expect(details(page).getByRole('link')).toHaveCount(1)
    await expect(details(page).getByText('Funções')).toBeVisible()
    await expect(details(page).getByText('Retorno de valores')).toBeVisible()
    await expect(
      details(page).getByText(
        'Esta memória orienta explicações; não altera sua proficiência.',
      ),
    ).toBeVisible()

    await details(page)
      .getByRole('button', { name: 'Fechar detalhes da memória' })
      .click()

    await expect(details(page)).toHaveCount(0)
    expect(searchOf(page).get('memory')).toBeNull()
  })

  test('reads a selected memory that is outside the active filter', async ({
    authenticatedPage: page,
  }) => {
    await page.setViewportSize(DESKTOP)
    const backend = await installMentorMemoriesBackend(page)

    await openMemoriesPage(page, {
      category: 'recurring_difficulty',
      memory: MEMORY_IDS.preference,
    })

    await expect(rows(page)).toHaveCount(2)
    await expect(
      details(page).getByRole('heading', {
        level: 2,
        name: 'Agora prefiro exemplos em Python.',
      }),
    ).toBeVisible()
    const [request] = backend.callsOf('get')
    expect(request?.data).toMatchObject({ memoryId: MEMORY_IDS.preference })
  })

  test('shows a message for a selected memory that does not exist', async ({
    authenticatedPage: page,
  }) => {
    await page.setViewportSize(DESKTOP)
    await installMentorMemoriesBackend(page)

    await openMemoriesPage(page, { memory: '01J7T8AC91Z5K8M4JQ8C2D6F9Z' })

    await expect(
      page.getByRole('heading', { name: 'Memória não encontrada' }),
    ).toBeVisible()
    await expect(rows(page)).toHaveCount(8)
  })

  test('edits a memory sending the expected version and shows the saved text', async ({
    authenticatedPage: page,
  }) => {
    await page.setViewportSize(DESKTOP)
    const backend = await installMentorMemoriesBackend(page)
    await openMemoriesPage(page, { memory: MEMORY_IDS.preference })

    await details(page).getByRole('button', { name: 'Editar' }).click()
    const field = page.getByRole('textbox', { name: 'Conteúdo' })
    await expect(page.getByRole('heading', { name: 'Editar memória' })).toBeVisible()
    await expect(field).toBeFocused()
    await field.fill('Prefiro exemplos longos em Python.')
    await page.getByRole('button', { name: 'Salvar memória' }).click()

    await expect(
      details(page).getByRole('heading', {
        level: 2,
        name: 'Prefiro exemplos longos em Python.',
      }),
    ).toBeVisible()
    await expect(rows(page).first()).toContainText('Prefiro exemplos longos em Python.')
    const [request] = backend.callsOf('edit')
    expect(request?.method).toBe('POST')
    expect(request?.data).toMatchObject({
      memoryId: MEMORY_IDS.preference,
      content: 'Prefiro exemplos longos em Python.',
      expectedVersion: 2,
    })
    expect(backend.callsOf('edit')).toHaveLength(1)
  })

  test('cancels an edit without a request and validates the content before saving', async ({
    authenticatedPage: page,
  }) => {
    await page.setViewportSize(DESKTOP)
    const backend = await installMentorMemoriesBackend(page)
    await openMemoriesPage(page, { memory: MEMORY_IDS.preference })

    await details(page).getByRole('button', { name: 'Editar' }).click()
    const field = page.getByRole('textbox', { name: 'Conteúdo' })
    await field.fill('')
    await page.getByRole('button', { name: 'Salvar memória' }).click()
    await expect(page.getByRole('alert')).toContainText('Escreva o conteúdo da memória.')
    await field.fill('a'.repeat(281))
    await expect(page.getByRole('alert')).toContainText('Use no máximo 280 caracteres.')
    await page.getByRole('button', { name: 'Salvar memória' }).click()
    await expect(page.getByRole('heading', { name: 'Editar memória' })).toBeVisible()
    await page.getByRole('button', { name: 'Cancelar' }).click()

    await expect(details(page)).toBeVisible()
    await expect(
      details(page).getByRole('heading', {
        level: 2,
        name: 'Agora prefiro exemplos em Python.',
      }),
    ).toBeVisible()
    expect(backend.callsOf('edit')).toHaveLength(0)
  })

  test('keeps the form open with the current content after an edit conflict', async ({
    authenticatedPage: page,
  }) => {
    await page.setViewportSize(DESKTOP)
    const backend = await installMentorMemoriesBackend(page)
    await openMemoriesPage(page, { memory: MEMORY_IDS.preference })

    await details(page).getByRole('button', { name: 'Editar' }).click()
    backend.bumpVersion(MEMORY_IDS.preference, 'Texto alterado em outro lugar.')
    await page.getByRole('textbox', { name: 'Conteúdo' }).fill('Meu texto novo.')
    await page.getByRole('button', { name: 'Salvar memória' }).click()

    const alert = page.getByRole('alert').filter({ hasText: 'Esta memória mudou' })
    await expect(alert).toContainText('Conteúdo atual: Texto alterado em outro lugar.')
    await expect(page.getByRole('heading', { name: 'Editar memória' })).toBeVisible()
    await expect(page.getByRole('textbox', { name: 'Conteúdo' })).toHaveValue(
      'Meu texto novo.',
    )
    expect(backend.callsOf('edit')[0]?.data).toMatchObject({ expectedVersion: 2 })

    await page.getByRole('button', { name: 'Salvar memória' }).click()

    await expect(
      details(page).getByRole('heading', { level: 2, name: 'Meu texto novo.' }),
    ).toBeVisible()
    expect(backend.callsOf('edit')[1]?.data).toMatchObject({ expectedVersion: 3 })
  })

  test('shows a save failure inline and lets the learner save again', async ({
    authenticatedPage: page,
  }) => {
    await page.setViewportSize(DESKTOP)
    const backend = await installMentorMemoriesBackend(page)
    await openMemoriesPage(page, { memory: MEMORY_IDS.preference })
    backend.failNext('edit')

    await details(page).getByRole('button', { name: 'Editar' }).click()
    await page.getByRole('textbox', { name: 'Conteúdo' }).fill('Novo texto.')
    await page.getByRole('button', { name: 'Salvar memória' }).click()

    await expect(page.getByRole('alert')).toContainText(
      'Não foi possível salvar a memória. Tente novamente.',
    )
    await expect(page.getByRole('button', { name: 'Salvar memória' })).toBeEnabled()
    await page.getByRole('button', { name: 'Salvar memória' }).click()

    await expect(
      details(page).getByRole('heading', { level: 2, name: 'Novo texto.' }),
    ).toBeVisible()
  })

  test('asks for confirmation before deleting and shows the removed notice afterwards', async ({
    authenticatedPage: page,
  }) => {
    await page.setViewportSize(DESKTOP)
    const backend = await installMentorMemoriesBackend(page)
    await openMemoriesPage(page, { memory: MEMORY_IDS.knowledge })

    await details(page).getByRole('button', { name: 'Excluir' }).click()
    const dialog = page.getByRole('alertdialog', { name: 'Excluir esta memória?' })
    await expect(dialog).toBeVisible()
    await dialog.getByRole('button', { name: 'Manter memória' }).click()
    await expect(dialog).toHaveCount(0)
    expect(backend.callsOf('remove')).toHaveLength(0)

    await details(page).getByRole('button', { name: 'Excluir' }).click()
    await page
      .getByRole('alertdialog', { name: 'Excluir esta memória?' })
      .getByRole('button', { name: 'Excluir memória' })
      .click()

    const notice = page.getByRole('region', { name: 'Memória excluída' })
    await expect(notice).toBeVisible()
    await expect(notice.getByRole('link', { name: 'Voltar ao Mentor' })).toBeVisible()
    await expect(rows(page)).toHaveCount(7)
    await expect(page.getByRole('button', { name: 'Todas · 7' })).toBeVisible()
    expect(searchOf(page).get('memory')).toBeNull()
    const [request] = backend.callsOf('remove')
    expect(request?.method).toBe('POST')
    expect(request?.data).toMatchObject({ memoryId: MEMORY_IDS.knowledge })
    await expect(
      rows(page).filter({ hasText: 'Conheço variáveis e condicionais em Python.' }),
    ).toHaveCount(0)
  })

  test('keeps the confirmation open with an error when the deletion fails', async ({
    authenticatedPage: page,
  }) => {
    await page.setViewportSize(DESKTOP)
    const backend = await installMentorMemoriesBackend(page)
    await openMemoriesPage(page, { memory: MEMORY_IDS.knowledge })
    backend.failNext('remove')

    await details(page).getByRole('button', { name: 'Excluir' }).click()
    const dialog = page.getByRole('alertdialog', { name: 'Excluir esta memória?' })
    await dialog.getByRole('button', { name: 'Excluir memória' }).click()

    await expect(dialog.getByRole('alert')).toContainText(
      'Não foi possível excluir a memória. Tente novamente.',
    )
    await dialog.getByRole('button', { name: 'Excluir memória' }).click()

    await expect(page.getByRole('region', { name: 'Memória excluída' })).toBeVisible()
    await expect(rows(page)).toHaveCount(7)
  })

  test('draws the same memories in the map with hub links and desktop concept links', async ({
    authenticatedPage: page,
  }) => {
    await page.setViewportSize(DESKTOP)
    await installMentorMemoriesBackend(page)
    await openMemoriesPage(page, { view: 'map' })

    const region = page.getByRole('region', { name: 'Mapa de memórias' })
    await expect(region.getByText('Suas memórias')).toBeVisible()
    await expect(mapNodes(page)).toHaveCount(8)
    await expect(region.locator('[data-testid^="rf__edge-hub-"]')).toHaveCount(8)
    await expect(region.locator('[data-testid^="rf__edge-concept-"]')).toHaveCount(2)
    const mapNames = (await mapNodes(page).evaluateAll((nodes) =>
      nodes.map((node) => node.getAttribute('aria-label')),
    )) as string[]
    await page.getByRole('tab', { name: 'Lista' }).click()
    const listTexts = await rows(page).allInnerTexts()
    expect(listTexts).toHaveLength(mapNames.length)
    for (const name of mapNames) {
      const content = name.split(': ').slice(1).join(': ')
      expect(listTexts.some((text) => text.includes(content))).toBe(true)
    }
  })

  test('selects a map node with the keyboard and opens its details', async ({
    authenticatedPage: page,
  }) => {
    await page.setViewportSize(DESKTOP)
    await installMentorMemoriesBackend(page)
    await openMemoriesPage(page, { view: 'map' })

    const node = page.getByRole('button', {
      name: `${CATEGORY_LABELS.recurring_difficulty}: Confundo exibir e retornar valores.`,
    })
    await expect(node).toBeVisible()
    await node.focus()
    await expect(node).toBeFocused()
    await page.keyboard.press('Enter')

    await expect.poll(() => searchOf(page).get('memory')).toBe(MEMORY_IDS.difficulty)
    await expect(node).toHaveAttribute('aria-pressed', 'true')
    await expect(
      details(page).getByRole('heading', {
        level: 2,
        name: 'Confundo exibir e retornar valores.',
      }),
    ).toBeVisible()

    const other = page.getByRole('button', {
      name: `${CATEGORY_LABELS.interest_or_intention}: Quero criar aplicações web.`,
    })
    await expect(other).toBeVisible()
    await other.focus()
    await page.keyboard.press('Space')
    await expect.poll(() => searchOf(page).get('memory')).toBe(MEMORY_IDS.interest)
  })

  test('zooms the map within its bounds', async ({ authenticatedPage: page }) => {
    await page.setViewportSize(DESKTOP)
    await installMentorMemoriesBackend(page)
    await openMemoriesPage(page, { view: 'map' })

    const zoomOutput = page.locator('output[aria-label^="Zoom do mapa"]')
    const reduce = page.getByRole('button', { name: 'Reduzir mapa' })
    // The initial zoom is the fitted viewport, so only the step and the bounds are fixed.
    await expect(zoomOutput).toHaveText(/^\d+%$/)
    const before = Number.parseInt((await zoomOutput.textContent()) ?? '0', 10)
    await page.getByRole('button', { name: 'Ampliar mapa' }).click()
    await expect(zoomOutput).toHaveText(`${before + 20}%`)
    for (let step = 0; step < 15 && (await reduce.isEnabled()); step += 1)
      await reduce.click()

    await expect(zoomOutput).toHaveText('25%')
    await expect(reduce).toBeDisabled()
    await expect(page.getByRole('button', { name: 'Ampliar mapa' })).toBeEnabled()
  })

  test('lays out the mobile list and map without horizontal overflow and with hub links only', async ({
    authenticatedPage: page,
  }) => {
    await page.setViewportSize(MOBILE)
    const backend = await installMentorMemoriesBackend(page)
    await openMemoriesPage(page)

    await expect(rows(page)).toHaveCount(8)
    await expectNoHorizontalOverflow(page)
    await expect(page.getByRole('button', { name: 'Categoria: Todas' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Todas · 8' })).toBeHidden()

    await page.getByRole('button', { name: 'Categoria: Todas' }).click()
    await page.getByRole('menuitemradio', { name: 'Dificuldades recorrentes' }).click()
    await expect(
      page.getByRole('button', { name: 'Categoria: Dificuldades recorrentes' }),
    ).toBeVisible()
    await expect(rows(page)).toHaveCount(2)
    expect(backend.callsOf('list').at(-1)?.data).toMatchObject({
      category: 'recurring_difficulty',
    })
    expect(searchOf(page).get('category')).toBe('recurring_difficulty')

    await page
      .getByRole('button', { name: 'Categoria: Dificuldades recorrentes' })
      .click()
    await page.getByRole('menuitemradio', { name: 'Todas', exact: true }).click()
    await expect(page.getByRole('tab', { name: 'Mapa' })).toBeHidden()
    await page.getByRole('button', { name: 'Ver Mapa' }).click()
    await expect(page.getByRole('button', { name: 'Ver Lista' })).toBeVisible()
    const region = page.getByRole('region', { name: 'Mapa de memórias' })
    await expect(mapNodes(page)).toHaveCount(8)
    await expect(region.locator('[data-testid^="rf__edge-hub-"]')).toHaveCount(8)
    await expect(region.locator('[data-testid^="rf__edge-concept-"]')).toHaveCount(0)
    await expectNoHorizontalOverflow(page)

    const nodeBox = await mapNodes(page).first().boundingBox()
    expect(nodeBox?.width ?? 0).toBeGreaterThanOrEqual(44)
    expect(nodeBox?.height ?? 0).toBeGreaterThanOrEqual(44)
    await mapNodes(page).first().click()
    const panel = details(page)
    await expect(panel).toBeVisible()
    const mapBox = await region.boundingBox()
    const panelBox = await panel.boundingBox()
    expect(panelBox?.y ?? 0).toBeGreaterThan((mapBox?.y ?? 0) + (mapBox?.height ?? 0) - 1)
    await expectNoHorizontalOverflow(page)
  })

  test('completes an edit using only the keyboard at the mobile width', async ({
    authenticatedPage: page,
  }) => {
    await page.setViewportSize(MOBILE)
    const backend = await installMentorMemoriesBackend(page)
    await openMemoriesPage(page, { memory: MEMORY_IDS.preference })

    await details(page).getByRole('button', { name: 'Editar' }).focus()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('textbox', { name: 'Conteúdo' })).toBeFocused()
    await page.keyboard.press('Control+A')
    await page.keyboard.type('Prefiro exemplos com Python.')
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')
    await expect(page.getByRole('button', { name: 'Salvar memória' })).toBeFocused()
    await page.keyboard.press('Enter')

    await expect(
      details(page).getByRole('heading', {
        level: 2,
        name: 'Prefiro exemplos com Python.',
      }),
    ).toBeVisible()
    expect(backend.callsOf('edit')).toHaveLength(1)
    await expectNoHorizontalOverflow(page)
  })
})
