import { Heading, Text, render } from 'react-email'

import { EmailLayout } from '../email-layout.js'

export type AccountErasureAlertEmailProps = {
  erasureId: string
  module: string
  failureCode: string
  closedAt: string
  dueAt: string
}

export const ACCOUNT_ERASURE_ALERT_SUBJECT =
  'Alerta de limpeza de conta pendente no Shifu'

export const ACCOUNT_ERASURE_ALERT_TEXT = [
  'Uma limpeza de dados de conta ultrapassou o prazo de 24 horas.',
  'Identificador da eliminação: {{erasure_id}}',
  'Módulo: {{module}}',
  'Falha: {{failure_code}}',
  'Encerramento: {{closed_at}}',
  'Prazo: {{due_at}}',
].join('\n')

const ALERT_PREVIEW = 'Uma limpeza de dados de conta ultrapassou o prazo de 24 horas.'

const HEADING_STYLE = {
  color: '#1d1b18',
  fontFamily: 'Georgia, Times New Roman, serif',
  fontSize: '30px',
  lineHeight: '36px',
  margin: '0 0 20px',
}

const TEXT_STYLE = {
  color: '#35312b',
  fontSize: '16px',
  lineHeight: '24px',
  margin: '0 0 16px',
}

export const AccountErasureAlertEmail = ({
  erasureId,
  module,
  failureCode,
  closedAt,
  dueAt,
}: AccountErasureAlertEmailProps) => {
  return (
    <EmailLayout preview={ALERT_PREVIEW}>
      <Heading style={HEADING_STYLE}>Limpeza de conta pendente</Heading>
      <Text style={TEXT_STYLE}>
        Uma limpeza de dados de conta ultrapassou o prazo de 24 horas.
      </Text>
      <Text style={TEXT_STYLE}>
        Identificador da eliminação: {erasureId}
        <br />
        Módulo: {module}
        <br />
        Falha: {failureCode}
        <br />
        Encerramento: {closedAt}
        <br />
        Prazo: {dueAt}
      </Text>
    </EmailLayout>
  )
}

export const renderAccountErasureAlertEmail = async (
  props: AccountErasureAlertEmailProps,
): Promise<{ subject: string; html: string }> => {
  return {
    subject: ACCOUNT_ERASURE_ALERT_SUBJECT,
    html: await render(<AccountErasureAlertEmail {...props} />),
  }
}
