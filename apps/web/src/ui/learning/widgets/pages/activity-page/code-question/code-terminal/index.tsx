import '@xterm/xterm/css/xterm.css'
import { type CodeTerminalProps, useCodeTerminal } from './use-code-terminal'

import './code-terminal.css'

export type { CodeTerminalProps } from './use-code-terminal'

export const CodeTerminal = (props: CodeTerminalProps) => {
  const { status, statusText, terminalElementRef, transcript } = useCodeTerminal(props)
  return (
    <section
      aria-label='Terminal de prática'
      className='flex h-[28rem] min-h-[28rem] min-w-0 flex-none flex-col bg-card lg:h-full lg:min-h-0'
    >
      <div className='flex min-h-12 items-center justify-between border-b border-border px-3 lg:h-10 lg:min-h-10'>
        <span className='text-sm font-medium'>Terminal</span>
        {status !== 'waiting-input' && statusText ? (
          <output aria-live='polite' className='text-xs text-muted-foreground'>
            {statusText}
          </output>
        ) : null}
      </div>
      <div
        className='min-h-0 min-w-0 flex-1 overflow-hidden p-3'
        ref={terminalElementRef}
        role='application'
        aria-label='Terminal interativo. Digite a entrada padrão e pressione Enter.'
      />
      <div
        role='log'
        aria-label='Transcrição do Terminal'
        aria-live='polite'
        className='code-terminal-transcript'
      >
        {transcript ||
          (status === 'unavailable'
            ? 'A prática está indisponível. Você ainda pode editar e avaliar.'
            : 'A saída da prática aparecerá aqui.')}
      </div>
    </section>
  )
}
