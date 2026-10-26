import { Button } from '@/ui/shadcn/button'
import { Input } from '@/ui/shadcn/input'
import { Textarea } from '@/ui/shadcn/textarea'
import { useHttpPanel, type HttpPanelProps } from './use-http-panel'

export const HttpPanel = (props: HttpPanelProps) => {
  const state = useHttpPanel(props)
  return (
    <section aria-label='Requisições HTTP' className='min-w-0 space-y-3 p-4'>
      <p className='text-sm text-muted-foreground'>
        Envie uma requisição à API deste projeto. Editar arquivos não envia requisições.
      </p>
      <div className='flex flex-wrap gap-2'>
        {props.examples.map((example) => (
          <Button
            key={example.key}
            variant='outline'
            onClick={() => state.handleExample(example)}
          >
            {example.title}
          </Button>
        ))}
      </div>
      <fieldset className='flex flex-wrap gap-1'>
        <legend className='mb-1 text-xs'>Método HTTP</legend>
        {(['GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'] as const).map(
          (method) => (
            <Button
              key={method}
              variant={state.method === method ? 'default' : 'outline'}
              aria-pressed={state.method === method}
              onClick={() => state.handleMethodChange(method)}
            >
              {method}
            </Button>
          ),
        )}
      </fieldset>
      <label htmlFor='integrated-http-path' className='block space-y-1 text-sm'>
        Rota da API
        <Input
          id='integrated-http-path'
          value={state.path}
          onChange={(event) => state.handlePathChange(event.target.value)}
          placeholder='/api/tasks'
          className='min-h-11 font-mono'
        />
      </label>
      {state.hasBody ? (
        <label htmlFor='integrated-http-body' className='block space-y-1 text-sm'>
          Corpo da requisição
          <Textarea
            id='integrated-http-body'
            value={state.body}
            onChange={(event) => state.handleBodyChange(event.target.value)}
            className='min-h-28 font-mono'
          />
        </label>
      ) : null}
      <div className='flex gap-2'>
        <Button
          disabled={!props.isReady || state.isSending}
          onClick={() => void state.handleSend()}
        >
          {state.isSending ? 'Enviando…' : 'Enviar requisição'}
        </Button>
        {state.isSending ? (
          <Button variant='outline' onClick={state.handleCancel}>
            Cancelar requisição
          </Button>
        ) : null}
      </div>
      {!props.isReady ? (
        <output className='text-sm text-muted-foreground'>
          Aguarde a API ficar pronta. Sua resposta continua editável.
        </output>
      ) : null}
      {state.error ? <p role='alert'>{state.error}</p> : null}
      {state.response ? (
        <div aria-live='polite' className='space-y-2'>
          <p>Status HTTP {state.response.status}</p>
          {state.response.truncated ? <p>Resposta truncada no limite de 1 MB.</p> : null}
          <pre className='max-h-80 overflow-auto whitespace-pre-wrap break-words font-mono text-xs'>
            {state.response.body}
          </pre>
        </div>
      ) : null}
    </section>
  )
}
