import '@xterm/xterm/css/xterm.css'
import { Button } from '@/ui/shadcn/button'
import { Input } from '@/ui/shadcn/input'
import { useTerminalPanel, type TerminalPanelProps } from './use-terminal-panel'
export const TerminalPanel = (props: TerminalPanelProps) => {
  const state = useTerminalPanel(props)
  return (
    <section
      aria-label='Terminal de prática'
      className='min-w-0 space-y-3 overflow-hidden p-3'
    >
      <div
        aria-hidden='true'
        className='h-80 min-w-0 overflow-hidden'
        ref={state.terminalRef}
      />
      <pre
        role='log'
        aria-label='Saída do terminal'
        className={
          state.hasTerminalError
            ? 'max-h-80 overflow-auto whitespace-pre-wrap font-mono text-xs'
            : 'sr-only'
        }
      >
        {props.transcript || 'A saída da prática aparecerá aqui.'}
      </pre>
      <p className='text-xs text-muted-foreground'>
        Comandos permitidos:{' '}
        {props.commands
          .map((item) => [item.executable, ...item.arguments].join(' '))
          .join(' · ')}
      </p>
      <label htmlFor='integrated-command' className='block space-y-1 text-sm'>
        Comando permitido
        <Input
          id='integrated-command'
          className='min-h-11 font-mono'
          value={state.command}
          onChange={(event) => state.handleCommandChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              event.preventDefault()
              void state.handleRun()
            }
          }}
        />
      </label>
      <Button
        variant='outline'
        disabled={state.isRunning}
        onClick={() => void state.handleRun()}
      >
        Enviar comando
      </Button>
      {state.error ? <p role='alert'>{state.error}</p> : null}
    </section>
  )
}
