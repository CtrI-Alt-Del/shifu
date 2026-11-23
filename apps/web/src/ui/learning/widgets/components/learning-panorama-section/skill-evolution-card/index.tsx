import { motion } from 'motion/react'

import { ENTRANCE_CARD } from '@/constants/motion-variants'
import type { EvolutionOption } from '@/core/learning/learning-panorama'
import { Button } from '@/ui/shadcn/button'
import { Select } from '@/ui/shadcn/select'
import { Skeleton } from '@/ui/shadcn/skeleton'
import { ChartFrame } from '@/ui/shared/widgets/components/chart-frame'
import { LineChart } from '@/ui/shared/widgets/components/line-chart'

import { useSkillEvolutionCard } from './use-skill-evolution-card'

export type SkillEvolutionCardProps = {
  options: EvolutionOption[]
  defaultSkillExperienceId: string | null
}

const TITLE = 'Evolução de uma Habilidade'
const NO_EVALUATION_MESSAGE =
  'Os pontos da evolução aparecerão depois das primeiras avaliações.'
const ERROR_MESSAGE = 'Não foi possível carregar a evolução desta Habilidade.'

export const SkillEvolutionCard = (props: SkillEvolutionCardProps) => {
  const {
    state,
    selectedSkillExperienceId,
    selectOptions,
    evolutionData,
    baselineLabel,
    description,
    isRetrying,
    handleSelectSkillExperience,
    handleRetry,
  } = useSkillEvolutionCard(props)

  const hasOptions = selectOptions.length > 0

  return (
    <motion.div className='h-full min-w-0' variants={ENTRANCE_CARD}>
      <ChartFrame
        action={
          hasOptions ? (
            <div className='flex flex-col gap-3 sm:flex-row sm:items-center'>
              <Select
                aria-label='Habilidade exibida no gráfico'
                className='sm:w-auto sm:min-w-64'
                onValueChange={handleSelectSkillExperience}
                options={selectOptions}
                placeholder='Selecione uma Habilidade'
                value={selectedSkillExperienceId}
              />
              {state === 'error' ? (
                <Button
                  disabled={isRetrying}
                  onClick={handleRetry}
                  type='button'
                  variant='outline'
                >
                  Tentar novamente
                </Button>
              ) : null}
              {state === 'error' ? (
                <p className='sr-only' role='alert'>
                  {ERROR_MESSAGE}
                </p>
              ) : null}
            </div>
          ) : undefined
        }
        columns={['Data', 'Resultado', 'Estimativa']}
        description={description}
        emptyMessage={
          state === 'empty'
            ? NO_EVALUATION_MESSAGE
            : state === 'error'
              ? ERROR_MESSAGE
              : undefined
        }
        rows={evolutionData}
        title={TITLE}
      >
        {state === 'loading' ? (
          <output
            aria-busy='true'
            aria-label='Carregando a evolução da Habilidade'
            className='block'
          >
            <Skeleton aria-hidden='true' className='h-[200px] w-full' />
          </output>
        ) : (
          <LineChart
            baselineLabel={baselineLabel}
            data={evolutionData}
            title={TITLE}
            tone='jade'
          />
        )}
      </ChartFrame>
    </motion.div>
  )
}
