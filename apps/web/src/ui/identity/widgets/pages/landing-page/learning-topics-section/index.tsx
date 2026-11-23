import { Icon } from '@/ui/shared/widgets/components/icon'

export const LearningTopicsSection = () => {
  return (
    <section
      aria-labelledby='landing-topics-title'
      className='landing-section landing-topics'
    >
      <div className='landing-section__heading landing-topics__heading'>
        <p className='landing-page__eyebrow'>Por onde começar</p>
        <h2 id='landing-topics-title'>Um primeiro tema. Um mundo de possibilidades.</h2>
        <p>
          A versão inicial começa com Lógica de Programação. Outros caminhos estão sendo
          preparados.
        </p>
      </div>
      <div className='landing-topics__list'>
        <article className='landing-topic landing-topic--available'>
          <span aria-hidden='true' className='landing-topic__icon'>
            <Icon name='file-json' size={19} />
          </span>
          <div>
            <h3>Lógica de Programação</h3>
            <p>Tema que valida a primeira versão do Shifu.</p>
          </div>
          <span className='landing-topic__status'>Disponível</span>
        </article>
        <article className='landing-topic'>
          <span aria-hidden='true' className='landing-topic__icon'>
            <Icon name='book-open' size={19} />
          </span>
          <div>
            <h3>Culinária</h3>
          </div>
          <span className='landing-topic__status'>Em breve</span>
        </article>
        <article className='landing-topic'>
          <span aria-hidden='true' className='landing-topic__icon'>
            <Icon name='message-circle' size={19} />
          </span>
          <div>
            <h3>Idiomas</h3>
          </div>
          <span className='landing-topic__status'>Em breve</span>
        </article>
      </div>
    </section>
  )
}
