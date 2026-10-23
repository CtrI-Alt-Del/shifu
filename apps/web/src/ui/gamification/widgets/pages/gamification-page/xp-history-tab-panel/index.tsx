import { Button } from '@/ui/shadcn/button'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { useXpHistoryTabPanel } from './use-xp-history-tab-panel'
import { XpHistorySummary } from './xp-history-summary'
import { XpHistoryTable } from './xp-history-table'

const PRESERVATION_NOTE =
  'O XP recebido permanece no histórico mesmo se você remover um objetivo ou uma habilidade.'

export const XpHistoryTabPanel = () => {
  const { entries, totalXp, state, isRetrying, handleRetry } = useXpHistoryTabPanel()

  if (state === 'loading') {
    return (
      <output
        aria-busy='true'
        aria-label='Carregando histórico de XP'
        className='block space-y-5 rounded-[14px] border border-border bg-card p-6'
      >
        <div aria-hidden='true' className='h-16 w-full animate-pulse rounded bg-muted' />
        <div aria-hidden='true' className='h-64 animate-pulse rounded bg-muted' />
        <span className='sr-only'>Carregando histórico de XP</span>
      </output>
    )
  }

  if (state === 'error') {
    return (
      <section
        aria-labelledby='gamification-xp-history-error-title'
        className='rounded-[14px] border border-border bg-card p-8 text-center'
        role='alert'
      >
        <Icon className='mx-auto text-selo-text' name='circle-alert' size={32} />
        <h3
          autoFocus
          className='mt-4 font-serif text-2xl'
          id='gamification-xp-history-error-title'
          tabIndex={-1}
        >
          Não foi possível carregar seu histórico
        </h3>
        <p className='mt-3 text-muted-foreground'>
          Seu XP continua salvo. Tente novamente em alguns instantes.
        </p>
        <Button
          className='mt-6'
          disabled={isRetrying}
          onClick={handleRetry}
          type='button'
        >
          Tentar novamente
        </Button>
      </section>
    )
  }

  return (
    <div className='space-y-8'>
      <XpHistorySummary totalXp={totalXp} />

      {state === 'empty' ? (
        <section
          aria-labelledby='gamification-xp-history-empty-title'
          className='rounded-[14px] border border-border bg-card p-8 text-center'
        >
          <Icon className='mx-auto text-muted-foreground' name='history' size={32} />
          <h3
            className='mt-4 font-serif text-2xl'
            id='gamification-xp-history-empty-title'
          >
            Você ainda não recebeu XP
          </h3>
          <p className='mt-3 text-muted-foreground'>
            Conclua um diagnóstico, domine uma Competência ou finalize uma Habilidade para
            ver seus primeiros registros aqui.
          </p>
        </section>
      ) : (
        <XpHistoryTable entries={entries} />
      )}

      <p className='text-[13px] text-muted-foreground'>{PRESERVATION_NOTE}</p>
    </div>
  )
}
