import type { Page } from '@playwright/test'

import { expect } from '../playwright'

/** Widths where the card footer changes layout: 640 px row, 1024 px four columns. */
export const IMAGE_CHOICE_FOOTER_WIDTHS = [390, 640, 700, 800, 1024, 1180, 1440] as const

/**
 * Asserts that every card footer keeps its label and status inside the card,
 * without clipping or horizontal page scroll.
 */
export async function expectImageChoiceFootersContained(page: Page) {
  const report = await page.evaluate(() => {
    const overflows: string[] = []
    for (const card of document.querySelectorAll('.image-choice-card')) {
      const cardBox = card.getBoundingClientRect()
      const footer = card.querySelector('.image-choice-footer')
      if (!footer) continue
      if (footer.scrollWidth > footer.clientWidth + 1)
        overflows.push(`footer scrolls: ${footer.scrollWidth} > ${footer.clientWidth}`)
      for (const part of footer.querySelectorAll(
        '.image-choice-label, .image-choice-status',
      )) {
        const box = part.getBoundingClientRect()
        if (box.left < cardBox.left - 0.5 || box.right > cardBox.right + 0.5)
          overflows.push(
            `${part.className} [${box.left}, ${box.right}] leaves card [${cardBox.left}, ${cardBox.right}]`,
          )
        // One text line is about 22 px tall: more means the text wrapped inside the footer.
        if (part.matches('.image-choice-label') && box.height > 28)
          overflows.push(`label wrapped to ${box.height}px`)
        if (box.bottom > cardBox.bottom + 0.5)
          overflows.push(`${part.className} leaves the card bottom`)
      }
    }
    return {
      overflows,
      pageScrolls: document.documentElement.scrollWidth > window.innerWidth,
    }
  })
  expect(report.overflows).toEqual([])
  expect(report.pageScrolls).toBe(false)
}
