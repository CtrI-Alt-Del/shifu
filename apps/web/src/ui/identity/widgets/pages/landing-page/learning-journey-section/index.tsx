import { Icon } from '@/ui/shared/widgets/components/icon'

const JOURNEY_STEPS = [
  {
    icon: 'target' as const,
    title: 'Descubra seu ponto de partida',
    description: 'Um diagnóstico ajuda a entender o que você já sabe.',
  },
  {
    icon: 'git-fork' as const,
    title: 'Siga um caminho feito para você',
    description: 'A prática acompanha suas habilidades e o seu ritmo.',
  },
  {
    icon: 'message-circle' as const,
    title: 'Pratique com orientação',
    description: 'Receba correções e retorne ao que ainda precisa de atenção.',
  },
  {
    icon: 'trending-up' as const,
    title: 'Veja o que está avançando',
    description: 'Acompanhe seu progresso e mantenha a constância, um passo por vez.',
  },
]

export const LearningJourneySection = () => {
  return (
    <section
      aria-labelledby='landing-journey-title'
      className='landing-section landing-journey'
    >
      <div className='landing-section__heading'>
        <p className='landing-page__eyebrow'>Uma jornada que faz sentido</p>
        <h2 id='landing-journey-title'>Aprender é uma sequência de passos.</h2>
        <p>Você sabe de onde partiu e entende por que cada etapa vem depois.</p>
      </div>
      <ol className='landing-journey__steps'>
        {JOURNEY_STEPS.map((step, index) => (
          <li className='landing-journey__step' key={step.title}>
            <span aria-hidden='true' className='landing-journey__step-number'>
              0{index + 1}
            </span>
            <span className='landing-journey__step-icon'>
              <Icon aria-hidden='true' name={step.icon} size={19} />
            </span>
            <h3>{step.title}</h3>
            <p>{step.description}</p>
          </li>
        ))}
      </ol>
    </section>
  )
}
