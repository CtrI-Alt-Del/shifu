import { ModulePageHeader } from '@/ui/shared/widgets/components/module-page-header'

const achievements = [
  {
    description: 'Você deu o primeiro passo no seu caminho.',
    state: 'Conquistada',
    title: 'Primeiro passo',
  },
  {
    description: 'Pratique em cinco dias diferentes.',
    state: '2 de 5 dias',
    title: 'Ritmo constante',
  },
  {
    description: 'Explore uma nova habilidade do currículo.',
    state: 'Bloqueada',
    title: 'Mente curiosa',
  },
] as const

export const GamificationPage = () => {
  return (
    <div className='space-y-10'>
      <ModulePageHeader
        description='Reconheça o esforço que sustenta seu aprendizado, sem transformar a jornada em uma competição.'
        eyebrow='Módulo gamificação'
        title='Cada passo merece ser visto.'
      />

      <section className='grid gap-4 lg:grid-cols-[1.25fr_1fr]'>
        <article className='rounded-3xl bg-primary p-7 text-primary-foreground shadow-brand sm:p-9'>
          <p className='text-sm font-bold uppercase tracking-[0.14em] text-primary-foreground/70'>
            Seu nível
          </p>
          <div className='mt-5 flex items-end gap-4'>
            <p className='font-serif text-6xl font-bold'>03</p>
            <p className='pb-2 font-semibold text-primary-foreground/80'>
              Aprendiz atento
            </p>
          </div>
          <div className='mt-7 h-2.5 overflow-hidden rounded-full bg-primary-foreground/20'>
            <div className='h-full w-[64%] rounded-full bg-card' />
          </div>
          <div className='mt-3 flex justify-between text-sm text-primary-foreground/70'>
            <span>640 XP</span>
            <span>1.000 XP para o próximo nível</span>
          </div>
        </article>
        <article className='rounded-3xl border border-border bg-card p-7 shadow-card sm:p-9'>
          <p className='text-sm font-bold uppercase tracking-[0.14em] text-primary'>
            Sequência atual
          </p>
          <p className='mt-4 font-serif text-5xl font-bold'>4 dias</p>
          <p className='mt-2 text-sm leading-6 text-muted-foreground'>
            Seu hábito está ganhando forma. Uma prática curta hoje já mantém o ritmo.
          </p>
          <ul className='mt-6 flex gap-2' aria-label='Dias praticados nesta semana'>
            {[
              ['segunda', 'S'],
              ['terça', 'T'],
              ['quarta', 'Q'],
              ['quinta', 'Q'],
              ['sexta', 'S'],
              ['sábado', 'S'],
              ['domingo', 'D'],
            ].map(([weekday, abbreviation], index) => (
              <li
                className={`grid size-8 place-items-center rounded-full text-xs font-bold ${index < 4 ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}
                key={weekday}
              >
                {abbreviation}
              </li>
            ))}
          </ul>
        </article>
      </section>

      <section>
        <p className='text-sm font-bold uppercase tracking-[0.14em] text-primary'>
          Conquistas
        </p>
        <h2 className='mt-2 font-serif text-2xl font-bold'>Marcos da sua jornada</h2>
        <div className='mt-5 grid gap-4 md:grid-cols-3'>
          {achievements.map((achievement) => {
            const locked = achievement.state === 'Bloqueada'

            return (
              <article
                className={`rounded-2xl border border-border bg-card p-6 shadow-card ${locked ? 'opacity-65' : ''}`}
                key={achievement.title}
              >
                <span
                  className={`grid size-12 place-items-center rounded-2xl text-xl ${locked ? 'bg-muted text-muted-foreground' : 'bg-accent text-primary'}`}
                >
                  {locked ? '·' : '✦'}
                </span>
                <h3 className='mt-5 font-serif text-xl font-bold'>{achievement.title}</h3>
                <p className='mt-2 text-sm leading-6 text-muted-foreground'>
                  {achievement.description}
                </p>
                <p className='mt-5 text-xs font-bold uppercase tracking-[0.12em] text-primary'>
                  {achievement.state}
                </p>
              </article>
            )
          })}
        </div>
      </section>
    </div>
  )
}
