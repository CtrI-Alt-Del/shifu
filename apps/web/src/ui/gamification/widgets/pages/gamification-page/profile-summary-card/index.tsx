export type ProfileSummaryCardProps = {
  level: number
  totalXp: number
  xpForNextLevel: number
}

export const ProfileSummaryCard = ({
  level,
  totalXp,
  xpForNextLevel,
}: ProfileSummaryCardProps) => (
  <article className='rounded-3xl bg-latao-solid p-7 text-on-latao shadow-brand sm:p-9'>
    <p className='text-sm font-bold uppercase tracking-[0.14em] text-on-latao/70'>
      Seu nível
    </p>
    <div className='mt-5 flex items-end gap-4'>
      <p className='font-serif text-6xl font-bold'>{String(level).padStart(2, '0')}</p>
    </div>
    <div className='mt-3 flex justify-between text-sm text-on-latao/70'>
      <span>{totalXp.toLocaleString('pt-BR')} XP</span>
      <span>{xpForNextLevel.toLocaleString('pt-BR')} XP para o próximo nível</span>
    </div>
  </article>
)
