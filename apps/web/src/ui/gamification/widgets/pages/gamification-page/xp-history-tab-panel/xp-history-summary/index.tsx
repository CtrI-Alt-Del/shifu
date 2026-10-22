type XpHistorySummaryProps = {
  totalXp: number
}

export const XpHistorySummary = ({ totalXp }: XpHistorySummaryProps) => {
  return (
    <div className='flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between'>
      <div className='space-y-2'>
        <h2 className='font-serif text-2xl'>Histórico de XP</h2>
        <p className='text-sm text-muted-foreground'>
          Veja de onde veio seu XP, do registro mais recente ao mais antigo.
        </p>
      </div>
      <div className='space-y-1'>
        <p className='text-[13px] text-muted-foreground'>XP acumulado</p>
        <p className='text-3xl text-latao-text'>{totalXp.toLocaleString('pt-BR')} XP</p>
      </div>
    </div>
  )
}
