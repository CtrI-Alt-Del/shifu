import {
  PRIVACY_CONTACT_EMAIL,
  PRIVACY_CONTACT_MAILTO,
} from '@/ui/identity/constants/privacy-contact'
import { Anchor } from '@/ui/shared/widgets/components/anchor'

export const PrivacyCard = () => (
  <section
    className='rounded-lg border border-border bg-card p-6'
    aria-labelledby='privacy-title'
  >
    <h2 id='privacy-title' className='text-base font-semibold'>
      Seus dados e privacidade
    </h2>
    <p className='mt-4 text-sm leading-6 text-muted-foreground'>
      Leia a Política de privacidade para entender como seus dados são usados. Para pedir
      acesso, correção ou exercer outros direitos, entre em contato com a equipe.
    </p>
    <div className='mt-4 flex flex-wrap gap-3'>
      <Anchor
        route='privacy'
        className='inline-flex min-h-11 items-center justify-center rounded-md border border-control-border px-4 text-sm font-semibold hover:bg-muted'
      >
        Consultar política de privacidade
      </Anchor>
      <a
        href={PRIVACY_CONTACT_MAILTO}
        className='inline-flex min-h-11 items-center justify-center rounded-md border border-control-border px-4 text-sm font-semibold hover:bg-muted'
      >
        Solicitar atendimento
      </a>
    </div>
    <p className='mt-4 text-xs leading-6 text-muted-foreground'>
      O botão abre seu aplicativo de e-mail. Você completa a mensagem e envia. Se
      preferir, copie o endereço abaixo:
    </p>
    <p className='mt-3 break-all text-sm font-semibold'>{PRIVACY_CONTACT_EMAIL}</p>
  </section>
)
