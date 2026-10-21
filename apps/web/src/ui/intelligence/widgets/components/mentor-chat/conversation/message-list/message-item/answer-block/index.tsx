import Markdown from 'react-markdown'
import rehypePrism from 'rehype-prism-plus'
import './answer-block.css'

export type AnswerBlockProps = { content: string }
export const AnswerBlock = ({ content }: AnswerBlockProps) => (
  <div className='mentor-answer-code min-w-0 space-y-3 break-words [&_pre]:max-w-full [&_pre]:overflow-x-auto [&_pre]:rounded-md [&_pre]:border [&_pre]:border-border [&_pre]:bg-muted [&_pre]:p-4 [&_code]:font-mono [&_code]:text-sm [&_ul]:list-inside [&_ul]:list-disc [&_ol]:list-inside [&_ol]:list-decimal [&_a]:underline'>
    <Markdown
      skipHtml
      allowedElements={[
        'p',
        'strong',
        'em',
        'ul',
        'ol',
        'li',
        'blockquote',
        'pre',
        'code',
        'a',
        'br',
        'h1',
        'h2',
        'h3',
        'hr',
        'span',
      ]}
      rehypePlugins={[[rehypePrism, { ignoreMissing: true }]]}
      components={{
        pre: ({ children }) => (
          <section aria-label='Trecho de código'>
            {/* biome-ignore lint/a11y/noNoninteractiveTabindex: keyboard users must scroll long code horizontally. */}
            <pre tabIndex={0}>{children}</pre>
          </section>
        ),
        a: ({ children, href }) => (
          <a href={href} rel='noopener noreferrer'>
            {children}
          </a>
        ),
      }}
    >
      {content}
    </Markdown>
  </div>
)
