import Markdown from 'react-markdown'
import rehypePrism from 'rehype-prism-plus/common'

import { useMaterialContent } from './use-material-content'

import './material-content.css'

export type MaterialContentProps = {
  content: string
}

export const MaterialContent = ({ content }: MaterialContentProps) => {
  const { blocks } = useMaterialContent({ content })

  return (
    <div className='max-w-[68ch] space-y-6 text-base leading-7 text-foreground'>
      {blocks.map((block) =>
        block.kind === 'code' ? (
          <section
            aria-label={
              block.language ? `Bloco de código em ${block.language}` : 'Bloco de código'
            }
            className='overflow-x-auto rounded-md border border-border bg-muted p-4'
            key={block.key}
            // biome-ignore lint/a11y/noNoninteractiveTabindex: A labelled region that scrolls horizontally must be reachable by keyboard (WCAG 2.1.1).
            tabIndex={0}
          >
            <Markdown
              allowedElements={['pre', 'code', 'div', 'span']}
              components={{
                pre: ({ children }) => (
                  <pre className='material-content-code font-mono text-[13px] leading-[21px] text-foreground'>
                    {children}
                  </pre>
                ),
              }}
              rehypePlugins={[[rehypePrism, { ignoreMissing: true }]]}
              skipHtml
            >
              {`\`\`\`${block.language ?? ''}\n${block.code}\n\`\`\``}
            </Markdown>
          </section>
        ) : (
          <p key={block.key}>
            {block.spans.map((span) =>
              span.kind === 'code' ? (
                <code
                  className='rounded-[3px] bg-muted px-1 py-0.5 font-mono text-[0.9em]'
                  key={span.key}
                >
                  {span.value}
                </code>
              ) : (
                <span key={span.key}>{span.value}</span>
              ),
            )}
          </p>
        ),
      )}
    </div>
  )
}
