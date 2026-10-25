import { Icon } from '@/ui/shared/widgets/components/icon'

import { useActivityXpRewardBand } from './use-activity-xp-reward-band'

export type ActivityXpRewardBandProps = {
  activityId: string
  attemptId: string
}

export const ActivityXpRewardBand = ({
  activityId,
  attemptId,
}: ActivityXpRewardBandProps) => {
  const state = useActivityXpRewardBand(activityId, attemptId)

  return (
    <section
      aria-atomic='true'
      aria-label='Recompensa de XP desta Atividade'
      aria-live='polite'
      className='flex items-center gap-3 rounded-md border border-border bg-card p-4'
    >
      {state.status === 'pending' ? (
        <>
          <Icon
            aria-hidden='true'
            className='animate-spin text-muted-foreground'
            name='loader-circle'
            size={20}
          />
          <p className='text-sm text-muted-foreground'>
            Confirmando o XP desta Atividade…
          </p>
        </>
      ) : null}

      {state.status === 'unavailable' ? (
        <>
          <Icon
            aria-hidden='true'
            className='text-muted-foreground'
            name='circle-alert'
            size={20}
          />
          <p className='text-sm text-muted-foreground'>
            Não foi possível confirmar o XP agora. Seu resultado continua salvo.
          </p>
        </>
      ) : null}

      {state.status === 'no-additional' ? (
        <>
          <Icon
            aria-hidden='true'
            className='text-muted-foreground'
            name='circle-dashed'
            size={20}
          />
          <div>
            <p className='text-sm text-foreground'>
              Esta tentativa não gerou XP adicional nesta Atividade.
            </p>
            {state.maximumXp !== null ? (
              <p className='mt-0.5 text-xs text-muted-foreground'>
                {state.grantedXp} de {state.maximumXp} XP já confirmados nesta Atividade.
              </p>
            ) : null}
          </div>
        </>
      ) : null}

      {state.status === 'granted' ? (
        <>
          <Icon
            aria-hidden='true'
            className='text-latao-solid'
            name='sparkles'
            size={20}
          />
          <div>
            <p className='font-mono text-xl font-semibold text-latao-text'>
              +{state.additionalXp.toLocaleString('pt-BR')} XP
            </p>
            <p className='mt-0.5 text-xs text-muted-foreground'>
              {state.grantedXp} de {state.maximumXp} XP confirmados nesta Atividade.
            </p>
          </div>
        </>
      ) : null}
    </section>
  )
}
