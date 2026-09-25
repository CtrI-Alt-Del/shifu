import { useMaterialContent } from './use-material-content'

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
            <pre className='font-mono text-[13px] leading-[21px] text-foreground'>
              <code>{block.code}</code>
            </pre>
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
