import { Icon } from '@/ui/shared/widgets/components/icon'

export const MentorSection = () => {
  return (
    <section aria-labelledby='landing-mentor-title' className='landing-mentor'>
      <div className='landing-mentor__mark' aria-hidden='true'>
        <Icon name='brain' size={24} />
      </div>
      <div className='landing-mentor__copy'>
        <p className='landing-page__eyebrow'>Conheça o Mentor</p>
        <h2 id='landing-mentor-title'>
          Uma pista na hora certa vale mais que uma resposta pronta.
        </h2>
        <p>
          O Mentor ajuda você a pensar e construir a própria solução. A inteligência
          artificial é usada com cuidado; sua jornada continua útil mesmo quando ela não
          está disponível.
        </p>
      </div>
      <ul aria-label='Princípios do Mentor' className='landing-mentor__principles'>
        <li>
          <Icon aria-hidden='true' name='sparkles' size={17} />
          Pistas para pensar
        </li>
        <li>
          <Icon aria-hidden='true' name='check' size={17} />
          Soluções construídas por você
        </li>
      </ul>
    </section>
  )
}
