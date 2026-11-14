import type { ReactFastifyPracticeStatus } from '@/core/learning/react-fastify-practice-runner'
const STATUS_LABELS: Record<ReactFastifyPracticeStatus, string> = {
  idle: 'Aguardando',
  starting: 'Iniciando',
  updating: 'Atualizando',
  ready: 'Pronto',
  error: 'Erro na prática',
  unavailable: 'Indisponível',
}
export type PreviewPanelProps = {
  frontendStatus: ReactFastifyPracticeStatus
  apiStatus: ReactFastifyPracticeStatus
  previewUrl: string | null
}
export const PreviewPanel = (props: PreviewPanelProps) => (
  <section
    aria-label='Prévia integrada'
    className='flex h-full min-h-96 min-w-0 flex-col'
  >
    <p
      aria-live='polite'
      className='border-b border-border p-3 text-xs text-muted-foreground'
    >
      Frontend: {STATUS_LABELS[props.frontendStatus]} · API:{' '}
      {STATUS_LABELS[props.apiStatus]}
    </p>
    {props.previewUrl ? (
      <iframe
        title='Prévia isolada React + Fastify'
        src={props.previewUrl}
        sandbox='allow-scripts allow-same-origin'
        referrerPolicy='no-referrer'
        className='min-h-96 w-full flex-1 bg-white'
      />
    ) : (
      <p className='p-4 text-sm text-muted-foreground'>
        A prévia está {STATUS_LABELS[props.frontendStatus].toLowerCase()}. Você pode
        continuar editando e avaliar sua resposta.
      </p>
    )}
  </section>
)
