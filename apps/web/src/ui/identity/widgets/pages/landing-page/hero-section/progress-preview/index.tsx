import { Icon } from '@/ui/shared/widgets/components/icon'

export const ProgressPreview = () => {
  return (
    <article aria-label='Exemplo ilustrativo de evolução' className='landing-preview'>
      <div className='landing-preview__topline'>
        <span className='landing-preview__label'>Exemplo ilustrativo</span>
        <span aria-hidden='true' className='landing-preview__orbit' />
      </div>
      <div className='landing-preview__course'>
        <span className='landing-preview__course-icon'>
          <Icon aria-hidden='true' name='file-json' size={18} />
        </span>
        <div>
          <p className='landing-preview__overline'>Seu objetivo</p>
          <h2>Lógica de Programação</h2>
        </div>
      </div>

      <div className='landing-preview__progress-heading'>
        <div>
          <p className='landing-preview__overline'>Ponto de partida</p>
          <p className='landing-preview__progress-copy'>4 de 8 habilidades exploradas</p>
        </div>
        <span className='landing-preview__progress-value'>50%</span>
      </div>
      <div
        aria-label='Exemplo de progresso: 50 por cento'
        aria-valuemax={100}
        aria-valuemin={0}
        aria-valuenow={50}
        className='landing-preview__progress-track'
        role='progressbar'
      >
        <span />
      </div>

      <div className='landing-preview__next-step'>
        <span aria-hidden='true' className='landing-preview__step-icon'>
          <Icon name='arrow-right' size={16} />
        </span>
        <div>
          <p className='landing-preview__overline'>Próximo passo</p>
          <p>Praticar decisões com condições</p>
        </div>
        <span className='landing-preview__step-count'>03</span>
      </div>
      <p className='landing-preview__disclaimer'>
        Dados demonstrativos. Sua jornada será só sua.
      </p>
    </article>
  )
}
