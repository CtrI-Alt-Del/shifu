import { motion } from 'motion/react'

import type { AiQuotaStatus } from '@/core/intelligence/ai-quota-usage'
import { ENTRANCE_FILL, ENTRANCE_SECTION } from '@/constants/motion-variants'
import { Button } from '@/ui/shadcn/button'
import { AnimatedNumber } from '@/ui/shared/widgets/components/animated-number'
import { MotionEntrance } from '@/ui/shared/widgets/components/motion-entrance'

import { useAiUsagePage } from './use-ai-usage-page'

// The board draws its 1 px stroke inside the 24 px padding, so the padding here is
// 23 px: border plus padding then give the board's 24 px inset and 302 px inner
// width on a 350 px mobile card.
const CARD_CLASS_NAME =
  'flex flex-col gap-5 rounded-xl border border-border bg-card p-[23px]'

const VALUE_CLASS_NAMES: Record<AiQuotaStatus, string> = {
  normal: 'text-foreground',
  near_limit: 'text-foreground',
  blocked: 'text-selo-text',
}

const FILL_CLASS_NAMES: Record<AiQuotaStatus, string> = {
  normal: 'bg-foreground',
  near_limit: 'bg-selo-text',
  blocked: 'bg-primary',
}

const SENTENCE_CLASS_NAMES: Record<AiQuotaStatus, string> = {
  normal: 'text-muted-foreground',
  near_limit: 'text-selo-text',
  blocked: 'text-selo-text',
}

const CardHeader = () => (
  <header className='flex flex-col gap-1'>
    <h2 className='text-base font-semibold leading-6' id='ai-usage-title'>
      Uso da IA
    </h2>
    <p className='text-sm text-muted-foreground'>
      Quanto da sua cota mensal de IA você já usou.
    </p>
  </header>
)

export const AiUsagePage = () => {
  const { viewState, status, percentage, renewalText, statusSentence, handleRetry } =
    useAiUsagePage()

  if (viewState === 'loading') {
    return (
      <div
        aria-busy='true'
        className='animate-pulse space-y-5 rounded-xl border border-border bg-card p-6 motion-reduce:animate-none'
      >
        <output aria-label='Carregando o uso da IA' className='sr-only'>
          Carregando o uso da IA
        </output>
        <div className='h-5 w-32 rounded bg-muted' />
        <div className='h-12 w-40 rounded bg-muted' />
        <div className='h-5 w-56 rounded bg-muted' />
      </div>
    )
  }

  if (viewState === 'unavailable' || status === null) {
    return (
      <section aria-labelledby='ai-usage-title' className={CARD_CLASS_NAME}>
        <CardHeader />
        <div className='flex flex-col items-start gap-4 sm:flex-row sm:items-center sm:justify-between'>
          <p className='text-sm text-foreground' role='alert'>
            Não foi possível carregar o uso da IA agora. Tente de novo em instantes.
          </p>
          {/* `!` because the global `* { border-color }` rule outranks layered utilities. */}
          <Button
            className='shrink-0 border-control-border!'
            onClick={handleRetry}
            variant='outline'
          >
            Tentar novamente
          </Button>
        </div>
      </section>
    )
  }

  const boundedPercentage = Math.min(100, Math.max(0, percentage))

  return (
    <MotionEntrance>
      <motion.section
        aria-labelledby='ai-usage-title'
        className={CARD_CLASS_NAME}
        variants={ENTRANCE_SECTION}
      >
        <CardHeader />
        <div className='flex flex-wrap items-end justify-between gap-x-4 gap-y-1'>
          <p className='flex items-end gap-2'>
            <AnimatedNumber
              className={`font-serif text-5xl leading-none ${VALUE_CLASS_NAMES[status]}`}
              format={(value) => `${value}%`}
              value={percentage}
            />
            <span className='text-sm leading-7 text-muted-foreground'>da cota usada</span>
          </p>
          <p className='text-sm text-muted-foreground'>{renewalText}</p>
        </div>
        <div
          aria-label='Cota de IA usada'
          aria-valuemax={100}
          aria-valuemin={0}
          aria-valuenow={boundedPercentage}
          aria-valuetext={`${boundedPercentage}%`}
          className='h-2 w-full overflow-hidden rounded-full bg-muted'
          role='progressbar'
        >
          <motion.div
            className={`h-full rounded-full ${FILL_CLASS_NAMES[status]}`}
            custom={boundedPercentage}
            variants={ENTRANCE_FILL}
          />
        </div>
        <p className={`text-sm ${SENTENCE_CLASS_NAMES[status]}`}>{statusSentence}</p>
      </motion.section>
    </MotionEntrance>
  )
}
