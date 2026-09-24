export type MaterialParagraphBlock = {
  kind: 'paragraph'
  key: string
  spans: readonly MaterialTextSpan[]
}

export type MaterialCodeBlock = {
  kind: 'code'
  key: string
  language: string | null
  code: string
}

export type MaterialBlock = MaterialParagraphBlock | MaterialCodeBlock

export type MaterialTextSpan = {
  kind: 'text' | 'code'
  key: string
  value: string
}

export type UseMaterialContentProps = {
  content: string
}

const FENCE = '```'

export function useMaterialContent({ content }: UseMaterialContentProps) {
  return { blocks: parseMaterialContent(content) }
}

export function parseMaterialContent(content: string): readonly MaterialBlock[] {
  const lines = content.replace(/\r\n/g, '\n').split('\n')
  const blocks: MaterialBlock[] = []
  let paragraph: string[] = []
  let code: string[] | null = null
  let language: string | null = null

  function flushParagraph() {
    const text = paragraph.join(' ').trim()
    paragraph = []

    if (!text) return

    blocks.push({
      kind: 'paragraph',
      key: `paragraph-${blocks.length}`,
      spans: parseSpans(text, blocks.length),
    })
  }

  function flushCode() {
    if (code === null) return

    blocks.push({
      kind: 'code',
      key: `code-${blocks.length}`,
      language,
      code: code.join('\n'),
    })
    code = null
    language = null
  }

  for (const line of lines) {
    if (line.trimStart().startsWith(FENCE)) {
      if (code === null) {
        flushParagraph()
        code = []
        language = line.trimStart().slice(FENCE.length).trim() || null
        continue
      }

      flushCode()
      continue
    }

    if (code !== null) {
      code.push(line)
      continue
    }

    if (!line.trim()) {
      flushParagraph()
      continue
    }

    paragraph.push(line.trim())
  }

  flushParagraph()
  flushCode()

  return blocks
}

function parseSpans(text: string, blockIndex: number): readonly MaterialTextSpan[] {
  const spans: MaterialTextSpan[] = []
  const segments = text.split('`')

  for (const [index, segment] of segments.entries()) {
    const isInlineCode = index % 2 === 1 && index < segments.length - 1

    if (!segment) continue

    spans.push({
      kind: isInlineCode ? 'code' : 'text',
      key: `span-${blockIndex}-${index}`,
      value: segment,
    })
  }

  return spans
}
