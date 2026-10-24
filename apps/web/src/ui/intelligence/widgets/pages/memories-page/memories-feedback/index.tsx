import { Button } from '@/ui/shadcn/button'
import { Skeleton } from '@/ui/shadcn/skeleton'

export type MemoriesFeedbackProps = {
  status: 'loading' | 'empty' | 'empty-filtered' | 'error' | 'not-found'
  onRetry: () => void
  onClearFilters: () => void
}

export const MemoriesFeedback = ({
  status,
  onRetry,
  onClearFilters,
}: MemoriesFeedbackProps) => {
  if (status === 'loading') {
    return (
      <div aria-busy='true' className='space-y-3'>
        <output className='sr-only'>Carregando memórias.</output>
        {[0, 1, 2, 3].map((item) => (
          <Skeleton className='h-20 w-full rounded-[10px]' key={item} />
        ))}
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div
        className='flex flex-col items-start gap-3 rounded-[10px] border border-border bg-card p-6'
        role='alert'
      >
        <h2 className='font-serif text-2xl font-normal'>
          Não foi possível carregar suas memórias
        </h2>
        <p className='text-sm text-muted-foreground'>
          O problema foi do Shifu. Tente novamente em instantes.
        </p>
        <Button
          onClick={onRetry}
          variant='ghost'
          className='border border-control-border'
        >
          Tentar novamente
        </Button>
      </div>
    )
  }

  if (status === 'not-found') {
    return (
      <div className='flex flex-col items-start gap-3 rounded-[10px] border border-border bg-card p-6'>
        <h2 className='font-serif text-2xl font-normal'>Memória não encontrada</h2>
        <p className='text-sm text-muted-foreground'>
          Esta memória não existe mais ou nunca esteve na sua conta.
        </p>
      </div>
    )
  }

  if (status === 'empty-filtered') {
    return (
      <div className='flex flex-col items-start gap-3 rounded-[10px] border border-border bg-card p-6'>
        <h2 className='font-serif text-2xl font-normal'>Nenhuma memória encontrada</h2>
        <p className='text-sm text-muted-foreground'>
          Nenhuma memória corresponde à busca ou ao filtro escolhido.
        </p>
        <Button
          onClick={onClearFilters}
          variant='ghost'
          className='border border-control-border'
        >
          Limpar filtros
        </Button>
      </div>
    )
  }

  return (
    <div className='flex flex-col items-start gap-3 rounded-[10px] border border-border bg-card p-6'>
      <h2 className='font-serif text-2xl font-normal'>Você ainda não tem memórias</h2>
      <p className='text-sm text-muted-foreground'>
        Quando você contar ao Mentor como prefere aprender, o que já sabe ou o que quer
        alcançar, ele registra aqui para adaptar as explicações.
      </p>
    </div>
  )
}
