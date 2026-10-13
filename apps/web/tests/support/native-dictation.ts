import type { Locator, Page } from '@playwright/test'
import { expect, navigateAuthenticatedPage } from '../playwright'

/** Controlled events prove UI composition, not native recognition quality. */
export async function installControlledDictation(
  page: Page,
  availability: 'available' | 'downloadable' = 'available',
) {
  await page.evaluate((availability) => {
    class ControlledRecognition {
      static current: ControlledRecognition | null = null
      static available = async () => availability
      static install = async () => true
      processLocally = false
      lang = ''
      continuous = false
      interimResults = false
      maxAlternatives = 1
      onstart: (() => void) | null = null
      onend: (() => void) | null = null
      onerror: (() => void) | null = null
      onnomatch: (() => void) | null = null
      onresult: ((event: unknown) => void) | null = null
      start() {
        ControlledRecognition.current = this
      }
      stop() {}
      abort() {
        ControlledRecognition.current = null
      }
    }
    Object.assign(window, { SpeechRecognition: ControlledRecognition })
  }, availability)
}

async function assertKeyboardControl(page: Page, control: Locator) {
  const box = await control.boundingBox()
  expect(box?.width).toBeGreaterThanOrEqual(44)
  expect(box?.height).toBeGreaterThanOrEqual(44)
  await control.focus()
  await page.keyboard.press('ArrowRight')
  await expect(control).toHaveAttribute('type', 'button')
  expect(await control.evaluate((element) => element.tabIndex)).toBe(0)
  await expect(control).toBeFocused()
  const ring = await control.evaluate((element) => {
    const style = getComputedStyle(element)
    return { width: Number.parseFloat(style.outlineWidth), style: style.outlineStyle }
  })
  expect(ring.width).toBeGreaterThan(0)
  expect(ring.style).not.toBe('none')
}

export async function exerciseDictationStates(
  page: Page,
  surface: 'page' | 'fab',
  width: number,
) {
  await page.setViewportSize({ width, height: width === 390 ? 900 : 1058 })
  await installControlledDictation(page)
  await navigateAuthenticatedPage(page, surface === 'page' ? '/intelligence/' : '/')
  if (surface === 'fab') await page.getByRole('button', { name: 'Abrir Mentor' }).click()
  const form = page.getByRole('form', { name: 'Enviar mensagem ao Mentor' })
  const draft = form.getByRole('textbox')
  await draft.fill('Rascunho anterior')
  await assertKeyboardControl(
    page,
    form.getByRole('button', { name: 'Gravar ditado', exact: true }),
  )
  await form.getByRole('button', { name: 'Gravar ditado', exact: true }).click()
  await expect(form.getByText('Preparando ditado…')).toBeVisible()
  await expect(form.getByRole('button', { name: 'Enviar', exact: true })).toBeDisabled()
  await page.evaluate(() => {
    const native = window as typeof window & {
      SpeechRecognition: { current: { onstart: (() => void) | null } }
    }
    native.SpeechRecognition.current.onstart?.()
  })
  await expect(form.getByText('Gravando ditado…')).toBeVisible()
  await expect(
    form.getByText('Fale sua mensagem. Ao encerrar, você poderá revisar o texto.'),
  ).toBeVisible()
  await expect(form.getByRole('button', { name: 'Cancelar', exact: true })).toBeVisible()
  const stop = form.getByRole('button', { name: 'Encerrar ditado' })
  await assertKeyboardControl(
    page,
    form.getByRole('button', { name: 'Cancelar', exact: true }),
  )
  await assertKeyboardControl(page, stop)
  const box = await stop.boundingBox()
  expect(box?.height).toBeGreaterThanOrEqual(44)
  await page.screenshot({
    path: `.playwright-cli/screenshots/shifu-105-${surface}-${width}-recording.png`,
  })
  await stop.click()
  await expect(form.getByText('Transcrevendo ditado…')).toBeVisible()
  await expect(
    form.getByText('O texto ficará disponível para você revisar antes de enviar.'),
  ).toBeVisible()
  await page.screenshot({
    path: `.playwright-cli/screenshots/shifu-105-${surface}-${width}-transcribing.png`,
  })
  await page.evaluate(() => {
    const native = window as typeof window & {
      SpeechRecognition: {
        current: {
          onresult: ((event: unknown) => void) | null
          onend: (() => void) | null
        }
      }
    }
    native.SpeechRecognition.current.onresult?.({
      resultIndex: 0,
      results: [{ isFinal: true, 0: { transcript: 'Como estudar funções em Python?' } }],
    })
    native.SpeechRecognition.current.onend?.()
  })
  await expect(form.getByText('Revise seu ditado')).toBeVisible()
  await expect(
    form.getByText('Edite o texto se precisar e toque em Enviar.'),
  ).toBeVisible()
  await expect(draft).toHaveValue('Rascunho anterior\nComo estudar funções em Python?')
  await expect(draft).toBeFocused()
  await expect(form.getByRole('button', { name: 'Enviar', exact: true })).toBeEnabled()
  await page.screenshot({
    path: `.playwright-cli/screenshots/shifu-105-${surface}-${width}-review.png`,
  })
  await draft.fill('Texto revisado explicitamente')
  await expect(draft).toHaveValue('Texto revisado explicitamente')
  await form.getByRole('button', { name: 'Gravar ditado', exact: true }).click()
  await form.getByRole('button', { name: 'Cancelar', exact: true }).click()
  await expect(draft).toHaveValue('Texto revisado explicitamente')
}

export async function exerciseLanguageInstallationControls(
  page: Page,
  surface: 'page' | 'fab',
) {
  await page.setViewportSize({ width: 390, height: 900 })
  await installControlledDictation(page, 'downloadable')
  await navigateAuthenticatedPage(page, surface === 'page' ? '/intelligence/' : '/')
  if (surface === 'fab') await page.getByRole('button', { name: 'Abrir Mentor' }).click()
  const form = page.getByRole('form', { name: 'Enviar mensagem ao Mentor' })
  await expect(
    form.getByText('Ditado indisponível neste navegador. Continue digitando.'),
  ).toBeVisible()
  await assertKeyboardControl(
    page,
    form.getByRole('button', { name: 'Instalar pacote de idioma' }),
  )
  await expect(form.getByRole('textbox')).toBeEnabled()
  expect(
    await page.evaluate(
      () =>
        (window as typeof window & { SpeechRecognition: { current: unknown } })
          .SpeechRecognition.current,
    ),
  ).toBeNull()
}
