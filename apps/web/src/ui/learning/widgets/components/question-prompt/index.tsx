import Markdown from 'react-markdown'
import rehypePrism from 'rehype-prism-plus/common'

import './question-prompt.css'

export type QuestionPromptProps = {
  id: string
  prompt: string
  size?: 'activity' | 'result'
}

export const QuestionPrompt = ({
  id,
  prompt,
  size = 'activity',
}: QuestionPromptProps) => (
  // Markdown code fences render block elements, which cannot be children of an h2.
  // biome-ignore lint/a11y/useSemanticElements: The prompt can contain block-level Markdown.
  <div
    aria-level={2}
    className={
      size === 'activity'
        ? 'min-w-0 space-y-4 font-serif text-3xl leading-tight text-foreground sm:text-4xl'
        : 'min-w-0 space-y-2 text-sm font-medium text-foreground'
    }
    id={id}
    role='heading'
  >
    <Markdown
      allowedElements={['p', 'pre', 'code', 'div', 'span', 'strong', 'em', 'br']}
      components={{
        p: ({ children }) => <p className='whitespace-pre-wrap'>{children}</p>,
        pre: ({ children }) => (
          <pre className='question-prompt-code overflow-x-auto rounded-md border border-border bg-background p-3 font-mono text-sm font-normal leading-relaxed text-foreground sm:bg-muted sm:p-4'>
            {children}
          </pre>
        ),
        code: ({ children, className }) => (
          <code
            className={
              className
                ? `${className} font-mono text-sm font-normal`
                : 'rounded bg-muted px-1 py-0.5 font-mono text-[0.85em] font-normal'
            }
          >
            {children}
          </code>
        ),
      }}
      rehypePlugins={[[rehypePrism, { ignoreMissing: true }]]}
      skipHtml
    >
      {prompt}
    </Markdown>
  </div>
)
