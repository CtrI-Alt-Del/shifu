import { Anchor } from '@/ui/shared/widgets/components/anchor'

import {
  PRIVACY_CONTACT_EMAIL,
  PRIVACY_CONTACT_MAILTO,
} from '@/ui/identity/constants/privacy-contact'

const POLICY_SECTIONS = [
  { href: '#controlador', label: 'Quem cuida dos seus dados' },
  { href: '#dados-finalidades', label: 'Dados, finalidades e bases legais' },
  { href: '#criancas-adolescentes', label: 'Crianças e adolescentes' },
  { href: '#cookies', label: 'Cookies necessários' },
  { href: '#ia-transferencias', label: 'Inteligência artificial e transferências' },
  { href: '#direitos', label: 'Seus direitos e atendimento' },
  { href: '#conservacao', label: 'Exclusão e conservação' },
  { href: '#atualizacoes', label: 'Atualizações desta política' },
] as const

export const PrivacyPolicyPage = () => {
  return (
    <div className='min-h-dvh bg-background text-foreground'>
      <header className='border-b border-border'>
        <div className='mx-auto flex h-20 w-full max-w-[1150px] items-center justify-between px-5 sm:px-8'>
          <Anchor
            aria-label='Shifu, página inicial'
            className='rounded-sm font-serif text-2xl leading-none text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-selo-text'
            route='root'
          >
            Shifu <span className='text-primary'>師</span>
          </Anchor>
          <Anchor
            className='min-h-11 rounded-md px-3 py-3 text-sm text-secondary-foreground underline-offset-4 hover:text-foreground hover:underline'
            route='login'
          >
            Entrar
          </Anchor>
        </div>
      </header>

      <main className='mx-auto w-full max-w-[1150px] px-5 pb-20 pt-12 sm:px-8 sm:pt-16'>
        <div>
          <h1 className='max-w-3xl font-serif text-4xl leading-[1.08] text-foreground sm:text-5xl'>
            Política de privacidade
          </h1>
          <p className='mt-5 max-w-2xl text-base leading-7 text-secondary-foreground sm:text-lg'>
            Saiba quais dados usamos, por que precisamos deles e como você pode exercer
            seus direitos.
          </p>
          <p className='mt-4 text-sm text-muted-foreground'>
            Versão 1.0. Atualizada em 21 de outubro de 2026.
          </p>
        </div>

        <div className='mt-12 grid min-w-0 gap-10 lg:mt-16 lg:grid-cols-[240px_minmax(0,740px)] lg:justify-between lg:gap-16'>
          <aside className='min-w-0 border-b border-border pb-8 lg:border-b-0 lg:pb-0'>
            <nav aria-label='Conteúdo da política'>
              <h2 className='font-sans text-sm font-semibold text-foreground'>
                Nesta página
              </h2>
              <ul className='mt-4 flex flex-col gap-1'>
                {POLICY_SECTIONS.map((section) => (
                  <li key={section.href}>
                    <a
                      className='block min-h-11 rounded-sm py-2 text-sm leading-5 text-secondary-foreground underline-offset-4 hover:text-foreground hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-selo-text'
                      href={section.href}
                    >
                      {section.label}
                    </a>
                  </li>
                ))}
              </ul>
            </nav>
          </aside>

          <article className='min-w-0 space-y-12'>
            <section
              aria-labelledby='controlador-title'
              className='scroll-mt-8 rounded-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-selo-text focus-visible:outline-offset-4'
              id='controlador'
              tabIndex={-1}
            >
              <h2
                className='font-sans text-xl font-semibold text-foreground sm:text-2xl'
                id='controlador-title'
                tabIndex={-1}
              >
                Quem cuida dos seus dados
              </h2>
              <div className='mt-4 space-y-4 leading-7 text-secondary-foreground'>
                <p>
                  A GSW é a controladora dos dados pessoais tratados na plataforma Shifu.
                  Isso significa que ela define as finalidades e os meios de tratamento
                  descritos nesta política.
                </p>
                <p>
                  A Encarregada pelo tratamento de dados pessoais é Gabriela da Silva.
                  Você pode falar com ela pelo canal de privacidade:{' '}
                  <a
                    className='break-all text-jade-text underline decoration-jade-text/60 underline-offset-4 hover:decoration-jade-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-selo-text'
                    href={PRIVACY_CONTACT_MAILTO}
                  >
                    {PRIVACY_CONTACT_EMAIL}
                  </a>
                  .
                </p>
              </div>
            </section>

            <section
              aria-labelledby='dados-finalidades-title'
              className='scroll-mt-8 rounded-sm border-t border-border pt-8 focus-visible:outline focus-visible:outline-2 focus-visible:outline-selo-text focus-visible:outline-offset-4'
              id='dados-finalidades'
              tabIndex={-1}
            >
              <h2
                className='font-sans text-xl font-semibold text-foreground sm:text-2xl'
                id='dados-finalidades-title'
                tabIndex={-1}
              >
                Dados, finalidades e bases legais
              </h2>
              <p className='mt-4 leading-7 text-secondary-foreground'>
                Tratamos apenas os dados adequados às finalidades abaixo. Para cada uso,
                indicamos a base legal da Lei Geral de Proteção de Dados Pessoais (LGPD).
              </p>

              <ul className='mt-6 divide-y divide-border'>
                <li className='py-5 first:pt-0'>
                  <h3 className='font-semibold text-foreground'>Conta e acesso</h3>
                  <p className='mt-2 leading-7 text-secondary-foreground'>
                    Nome de exibição, e-mail, credencial protegida e dados de sessão
                    permitem criar e proteger a conta e autenticar seu acesso. Usamos
                    esses dados para cumprir o contrato (art. 7º, V, da LGPD) e proteger a
                    sessão com base em legítimo interesse (art. 7º, IX).
                  </p>
                </li>
                <li className='py-5'>
                  <h3 className='font-semibold text-foreground'>Aprendizagem</h3>
                  <p className='mt-2 leading-7 text-secondary-foreground'>
                    Objetivos, respostas, tentativas, avaliações e progresso são usados
                    para oferecer e personalizar sua experiência de aprendizagem. A base é
                    a execução do contrato (art. 7º, V, da LGPD).
                  </p>
                </li>
                <li className='py-5'>
                  <h3 className='font-semibold text-foreground'>Mentor</h3>
                  <p className='mt-2 leading-7 text-secondary-foreground'>
                    Mensagens, memórias, anexos e conteúdo extraído que você envia são
                    usados para responder às solicitações feitas ao Mentor e manter o
                    contexto das conversas. A base é a execução do contrato (art. 7º, V,
                    da LGPD). Você escolhe se envia conteúdo ao Mentor; não inclua dados
                    pessoais sensíveis que não sejam necessários.
                  </p>
                </li>
                <li className='py-5'>
                  <h3 className='font-semibold text-foreground'>Gamificação</h3>
                  <p className='mt-2 leading-7 text-secondary-foreground'>
                    XP, nível, sequência de prática e conquistas permitem oferecer os
                    recursos de gamificação. A base é a execução do contrato (art. 7º, V,
                    da LGPD).
                  </p>
                </li>
                <li className='py-5'>
                  <h3 className='font-semibold text-foreground'>Comunicações</h3>
                  <p className='mt-2 leading-7 text-secondary-foreground'>
                    Destinatário, conteúdo de mensagens transacionais e dados de entrega
                    são tratados para enviar comunicações necessárias à conta e ao
                    serviço. A base é a execução do contrato (art. 7º, V, da LGPD) ou o
                    cumprimento de obrigação legal (art. 7º, II), conforme a mensagem.
                  </p>
                </li>
                <li className='py-5'>
                  <h3 className='font-semibold text-foreground'>Segurança e operação</h3>
                  <p className='mt-2 leading-7 text-secondary-foreground'>
                    Registros de acesso, dados técnicos e comunicações sobre solicitações
                    ajudam a proteger e operar a plataforma e a responder a você. Para a
                    segurança, usamos legítimo interesse (art. 7º, IX); quando a
                    conservação for exigida por lei, a base é o cumprimento de obrigação
                    legal (art. 7º, II).
                  </p>
                </li>
              </ul>
            </section>

            <section
              aria-labelledby='criancas-adolescentes-title'
              className='scroll-mt-8 rounded-sm border-t border-border pt-8 focus-visible:outline focus-visible:outline-2 focus-visible:outline-selo-text focus-visible:outline-offset-4'
              id='criancas-adolescentes'
              tabIndex={-1}
            >
              <h2
                className='font-sans text-xl font-semibold text-foreground sm:text-2xl'
                id='criancas-adolescentes-title'
                tabIndex={-1}
              >
                Crianças e adolescentes
              </h2>
              <div className='mt-4 space-y-4 leading-7 text-secondary-foreground'>
                <p>
                  O Shifu pode ser usado por crianças e adolescentes. Nesses casos, o
                  melhor interesse e a proteção da privacidade orientam o tratamento,
                  conforme o art. 14 da LGPD e o Estatuto Digital da Criança e do
                  Adolescente.
                </p>
                <p>
                  Por padrão, a experiência mantém os dados de aprendizagem privados e
                  aplica as opções de privacidade mais protetivas disponíveis. O Shifu não
                  oferece perfis públicos, publicidade comportamental ou ranking público.
                  A família e os responsáveis legais devem orientar e acompanhar o uso de
                  acordo com a idade e o desenvolvimento de cada pessoa.
                </p>
                <p>
                  Quando o consentimento for a base legal aplicável ao tratamento de dados
                  de uma criança, ele será específico e destacado, dado por pelo menos um
                  dos pais ou responsável legal. Consentimento não é a única base legal
                  possível: cada tratamento deve respeitar seu propósito e o melhor
                  interesse.
                </p>
                <p>
                  As respostas do Mentor são geradas por inteligência artificial, e não
                  por uma pessoa. Elas podem conter erros ou não ser adequadas a todas as
                  situações. O serviço aplica medidas para reduzir riscos e proteger a
                  privacidade, a segurança e o desenvolvimento de crianças e adolescentes.
                </p>
              </div>
            </section>

            <section
              aria-labelledby='cookies-title'
              className='scroll-mt-8 rounded-sm border-t border-border pt-8 focus-visible:outline focus-visible:outline-2 focus-visible:outline-selo-text focus-visible:outline-offset-4'
              id='cookies'
              tabIndex={-1}
            >
              <h2
                className='font-sans text-xl font-semibold text-foreground sm:text-2xl'
                id='cookies-title'
                tabIndex={-1}
              >
                Cookies necessários
              </h2>
              <div className='mt-4 space-y-4 leading-7 text-secondary-foreground'>
                <p>
                  Usamos cookies técnicos necessários para manter sua sessão e proteger o
                  acesso à conta. Eles guardam informações de autenticação e segurança
                  enquanto você usa o serviço ou até que expirem.
                </p>
                <p>
                  Não usamos cookies de publicidade nem de análise de navegação. Os
                  cookies necessários não são usados para acompanhar você em outros sites.
                </p>
              </div>
            </section>

            <section
              aria-labelledby='ia-transferencias-title'
              className='scroll-mt-8 rounded-sm border-t border-border pt-8 focus-visible:outline focus-visible:outline-2 focus-visible:outline-selo-text focus-visible:outline-offset-4'
              id='ia-transferencias'
              tabIndex={-1}
            >
              <h2
                className='font-sans text-xl font-semibold text-foreground sm:text-2xl'
                id='ia-transferencias-title'
                tabIndex={-1}
              >
                Inteligência artificial e transferências
              </h2>
              <div className='mt-4 space-y-4 leading-7 text-secondary-foreground'>
                <p>
                  Quando você pede ajuda ao Mentor ou uma avaliação que usa inteligência
                  artificial, o Shifu encaminha o contexto necessário à tarefa a
                  provedores de modelos. Entre eles estão OpenRouter, OpenAI, Amazon
                  Bedrock e DeepSeek. Não enviamos dados de conta, como sua senha, para
                  gerar uma resposta.
                </p>
                <p>
                  A infraestrutura desses provedores pode processar dados nos Estados
                  Unidos, na China ou em outros países, conforme o modelo e a rota usada.
                  O endpoint global da OpenRouter não fixa um país único. Para essas
                  transferências internacionais, são adotadas cláusulas-padrão contratuais
                  aprovadas pela ANPD e medidas complementares de proteção. As
                  configurações dos provedores solicitam retenção zero dos dados de
                  inferência e bloqueio de coleta para treinamento.
                </p>
                <p>
                  A retenção zero solicitada aos provedores não apaga as conversas,
                  memórias e registros que o próprio Shifu mantém para oferecer o serviço.
                  Eles seguem os prazos desta política.
                </p>
                <p>
                  As mensagens transacionais são entregues por um provedor SMTP que opera
                  no Brasil. Esse provedor recebe o endereço de e-mail, o conteúdo da
                  mensagem e os dados necessários para registrar a entrega.
                </p>
              </div>
            </section>

            <section
              aria-labelledby='direitos-title'
              className='scroll-mt-8 rounded-sm border-t border-border pt-8 focus-visible:outline focus-visible:outline-2 focus-visible:outline-selo-text focus-visible:outline-offset-4'
              id='direitos'
              tabIndex={-1}
            >
              <h2
                className='font-sans text-xl font-semibold text-foreground sm:text-2xl'
                id='direitos-title'
                tabIndex={-1}
              >
                Seus direitos e atendimento
              </h2>
              <p className='mt-4 leading-7 text-secondary-foreground'>
                Conforme a LGPD, você pode pedir, entre outros direitos aplicáveis ao seu
                caso:
              </p>
              <ul className='mt-4 list-disc space-y-2 pl-6 leading-7 text-secondary-foreground marker:text-jade-text'>
                <li>confirmação de que tratamos seus dados e acesso a eles;</li>
                <li>correção de dados incompletos, inexatos ou desatualizados;</li>
                <li>
                  anonimização, bloqueio ou eliminação de dados desnecessários, excessivos
                  ou tratados em desconformidade com a LGPD;
                </li>
                <li>
                  portabilidade, observadas a regulamentação e a proteção de segredos
                  comercial e industrial;
                </li>
                <li>
                  informação sobre compartilhamentos e sobre a possibilidade de não
                  fornecer consentimento e as consequências dessa escolha, quando ele for
                  solicitado;
                </li>
                <li>
                  revogação do consentimento e eliminação dos dados tratados com essa
                  base, ressalvadas as hipóteses legais de conservação;
                </li>
                <li>
                  oposição a tratamento realizado sem consentimento quando houver
                  descumprimento da LGPD; e
                </li>
                <li>
                  revisão de decisões tomadas unicamente com base em tratamento
                  automatizado que afetem seus interesses, quando aplicável.
                </li>
                <li>
                  petição à Autoridade Nacional de Proteção de Dados (ANPD) sobre seus
                  dados pessoais.
                </li>
              </ul>
              <div className='mt-6 space-y-4 leading-7 text-secondary-foreground'>
                <p>
                  Para exercer um direito ou tirar dúvidas, escreva para a Encarregada:{' '}
                  <a
                    className='break-all text-jade-text underline decoration-jade-text/60 underline-offset-4 hover:decoration-jade-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-selo-text'
                    href={PRIVACY_CONTACT_MAILTO}
                  >
                    {PRIVACY_CONTACT_EMAIL}
                  </a>
                  . Descreva o pedido e, se possível, use o e-mail cadastrado. Podemos
                  solicitar informações proporcionais para confirmar sua identidade. Não
                  envie senhas ou códigos de acesso.
                </p>
                <p>
                  O canal continua disponível após o encerramento da conta. O envio de uma
                  mensagem abre seu cliente de e-mail e não confirma que o Shifu recebeu o
                  pedido.
                </p>
                <p>
                  Para consultar as normas citadas, acesse a{' '}
                  <a
                    className='text-jade-text underline decoration-jade-text/60 underline-offset-4 hover:decoration-jade-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-selo-text'
                    href='https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm'
                    rel='noreferrer'
                    target='_blank'
                  >
                    LGPD
                  </a>
                  , o{' '}
                  <a
                    className='text-jade-text underline decoration-jade-text/60 underline-offset-4 hover:decoration-jade-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-selo-text'
                    href='https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2014/lei/l12965.htm'
                    rel='noreferrer'
                    target='_blank'
                  >
                    Marco Civil da Internet
                  </a>{' '}
                  e o{' '}
                  <a
                    className='text-jade-text underline decoration-jade-text/60 underline-offset-4 hover:decoration-jade-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-selo-text'
                    href='https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2025/lei/l15211.htm'
                    rel='noreferrer'
                    target='_blank'
                  >
                    Estatuto Digital da Criança e do Adolescente
                  </a>
                  .
                </p>
              </div>
            </section>

            <section
              aria-labelledby='conservacao-title'
              className='scroll-mt-8 rounded-sm border-t border-border pt-8 focus-visible:outline focus-visible:outline-2 focus-visible:outline-selo-text focus-visible:outline-offset-4'
              id='conservacao'
              tabIndex={-1}
            >
              <h2
                className='font-sans text-xl font-semibold text-foreground sm:text-2xl'
                id='conservacao-title'
                tabIndex={-1}
              >
                Exclusão e conservação
              </h2>
              <div className='mt-4 space-y-4 leading-7 text-secondary-foreground'>
                <p>
                  Você pode pedir o encerramento da conta e a eliminação de dados pessoais
                  pelo canal de privacidade. Depois da confirmação do encerramento, o
                  acesso é interrompido imediatamente e os dados da conta nos sistemas
                  ativos são eliminados em até 24 horas, salvo conservação permitida ou
                  exigida por lei.
                </p>
                <p>
                  Registros de acesso à aplicação são conservados por seis meses, conforme
                  o art. 15 do Marco Civil da Internet. Esse prazo se aplica a essa
                  categoria específica, não a todos os seus dados. Outros registros
                  técnicos são mantidos somente pelo tempo necessário à segurança, à
                  operação e às obrigações legais aplicáveis.
                </p>
                <p>
                  Cópias de segurança que ainda contenham dados excluídos expiram em até
                  30 dias após a eliminação dos sistemas ativos. Se uma cópia for
                  restaurada, a eliminação é reaplicada antes do uso dos dados.
                </p>
                <p>
                  Podemos conservar dados mínimos pelo período necessário para cumprir uma
                  obrigação legal, exercer direitos em processos ou atender outra hipótese
                  prevista na LGPD. Quando a finalidade termina, eliminamos ou
                  anonimizamos os dados, conforme a lei.
                </p>
              </div>
            </section>

            <section
              aria-labelledby='atualizacoes-title'
              className='scroll-mt-8 rounded-sm border-t border-border pt-8 focus-visible:outline focus-visible:outline-2 focus-visible:outline-selo-text focus-visible:outline-offset-4'
              id='atualizacoes'
              tabIndex={-1}
            >
              <h2
                className='font-sans text-xl font-semibold text-foreground sm:text-2xl'
                id='atualizacoes-title'
                tabIndex={-1}
              >
                Atualizações desta política
              </h2>
              <p className='mt-4 leading-7 text-secondary-foreground'>
                Esta política pode mudar para refletir alterações no Shifu ou nas leis
                aplicáveis. Quando isso acontecer, atualizaremos o número da versão e a
                data indicados no início da página. Consulte esta página para acompanhar a
                versão vigente.
              </p>
            </section>

            <footer className='border-t border-border pt-8'>
              <h2 className='font-serif text-2xl text-foreground'>
                Fale com a Encarregada
              </h2>
              <p className='mt-3 leading-7 text-secondary-foreground'>
                Para assuntos sobre seus dados pessoais, escreva para{' '}
                <a
                  className='break-all text-jade-text underline decoration-jade-text/60 underline-offset-4 hover:decoration-jade-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-selo-text'
                  href={PRIVACY_CONTACT_MAILTO}
                >
                  {PRIVACY_CONTACT_EMAIL}
                </a>
                .
              </p>
              <p className='mt-5 text-sm text-muted-foreground'>
                Shifu · Política de privacidade · Versão 1.0 · 21 de outubro de 2026
              </p>
            </footer>
          </article>
        </div>
      </main>
    </div>
  )
}
