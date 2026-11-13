import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ROUTES } from '@/constants/routes'
import { PlanningRequestError } from '@/ui/intelligence/hooks/planning-request-error'
import { useAiQuotaBlock } from '@/ui/intelligence/hooks/use-ai-quota-block'
import { useStartPlanningAction } from '@/ui/intelligence/hooks/use-start-planning-action'
import { consumePlanningEntry } from '@/ui/intelligence/planning-entry'
import type { AnchorProps } from '@/ui/shared/widgets/components/anchor'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'

import { PlanningIntentComposer } from '..'

// `usePlanningIntentComposer` owns the validation/submission behavior under
// test (CA-07, CA-08); it is exercised for real here, mocking only the
// colocated single-consumer action hook and the shared navigation wrapper
// below it, per widget-testing-rules ("mock a domain query/action hook
// rather than a generic useQuery result").
vi.mock('@/ui/intelligence/hooks/use-start-planning-action', () => ({
  useStartPlanningAction: vi.fn(),
}))

vi.mock('@/ui/intelligence/hooks/use-ai-quota-block', () => ({
  useAiQuotaBlock: vi.fn(),
}))

vi.mock('@/ui/shared/widgets/components/anchor', () => ({
  Anchor: ({ children, route, ...props }: AnchorProps) => (
    <a href={ROUTES[route]} {...props}>
      {typeof children === 'function' ? children({ isActive: false }) : children}
    </a>
  ),
}))

vi.mock('@/ui/shared/hooks/use-navigation', () => ({
  useNavigation: vi.fn(),
}))

const startPlanningMock = vi.fn()
const navigateToMock = vi.fn()
const navigateToPlannerMock = vi.fn()
const useStartPlanningActionMock = vi.mocked(useStartPlanningAction)
const useNavigationMock = vi.mocked(useNavigation)
const useAiQuotaBlockMock = vi.mocked(useAiQuotaBlock)
const BLOCKED_MESSAGE =
  'Sua cota de IA acabou. O planejamento com IA volta em 1º de dezembro de 2026. Você pode criar um Objetivo manualmente agora.'

/** The reading says blocked, or the start was refused on this screen. */
function mockQuotaReading(isReadingBlocked: boolean) {
  useAiQuotaBlockMock.mockImplementation((hasRefusal = false) => ({
    isAiQuotaBlocked: isReadingBlocked || hasRefusal,
    isAiQuotaNearLimit: false,
    getAiQuotaBlockedMessage: (surface) => (surface === 'home' ? BLOCKED_MESSAGE : ''),
    aiQuotaBlockedRole: hasRefusal ? 'alert' : 'status',
    aiQuotaAccountId: 'account-1',
    aiQuotaPercentage: 100,
    aiQuotaRenewsOn: '2026-12-01',
  }))
}

describe('PlanningIntentComposer', () => {
  afterEach(cleanup)

  beforeEach(() => {
    vi.clearAllMocks()
    mockQuotaReading(false)
    useStartPlanningActionMock.mockReturnValue({
      error: null,
      isPending: false,
      startPlanning: startPlanningMock,
    })
    useNavigationMock.mockReturnValue({
      refreshCurrentRoute: vi.fn(),
      navigateTo: navigateToMock,
      navigateToActivity: vi.fn(),
      navigateToGoalDetail: vi.fn(),
      navigateToPlanner: navigateToPlannerMock,
    })
  })

  it('renders the intent field and the manual-creation link, with the primary action always enabled', () => {
    render(<PlanningIntentComposer />)

    expect(
      screen.getByRole('heading', { name: 'O que você quer aprender?' }),
    ).toBeVisible()
    expect(screen.getByLabelText('O que você quer aprender?')).toHaveValue('')
    expect(screen.getByRole('link', { name: 'Criar manualmente' })).toHaveAttribute(
      'href',
      ROUTES.learningGoalsNew,
    )
    expect(screen.getByRole('button', { name: 'Planejar com IA' })).toBeEnabled()
  })

  it('rejects an empty intent before sending any request and keeps focus on the field (CA-07)', () => {
    render(<PlanningIntentComposer />)

    fireEvent.click(screen.getByRole('button', { name: 'Planejar com IA' }))

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Descreva o que você quer aprender antes de continuar.',
    )
    expect(startPlanningMock).not.toHaveBeenCalled()
    expect(screen.getByLabelText('O que você quer aprender?')).toHaveFocus()
  })

  it('rejects a whitespace-only intent the same way (CA-07)', () => {
    render(<PlanningIntentComposer />)
    const textarea = screen.getByLabelText('O que você quer aprender?')

    fireEvent.change(textarea, { target: { value: '   ' } })
    fireEvent.click(screen.getByRole('button', { name: 'Planejar com IA' }))

    expect(screen.getByRole('alert')).toBeVisible()
    expect(startPlanningMock).not.toHaveBeenCalled()
    expect(textarea).toHaveFocus()
  })

  it('clears the validation message once the learner edits the field again', () => {
    render(<PlanningIntentComposer />)
    fireEvent.click(screen.getByRole('button', { name: 'Planejar com IA' }))
    expect(screen.getByRole('alert')).toBeVisible()

    fireEvent.change(screen.getByLabelText('O que você quer aprender?'), {
      target: { value: 'quero aprender Python' },
    })

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('starts planning with the trimmed intent and navigates to the returned planning id', () => {
    startPlanningMock.mockImplementation(
      (_intent: string, options?: { onSuccess?: (session: { id: string }) => void }) => {
        options?.onSuccess?.({ id: 'planning-123' })
      },
    )
    render(<PlanningIntentComposer />)

    fireEvent.change(screen.getByLabelText('O que você quer aprender?'), {
      target: { value: '  quero aprender Python  ' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Planejar com IA' }))

    expect(startPlanningMock).toHaveBeenCalledWith(
      'quero aprender Python',
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    )
    expect(navigateToPlannerMock).toHaveBeenCalledWith('planning-123')
    expect(consumePlanningEntry('planning-123')).toBe(true)
  })

  it('shows a pending state and disables the field while a session is starting', () => {
    useStartPlanningActionMock.mockReturnValue({
      error: null,
      isPending: true,
      startPlanning: startPlanningMock,
    })
    render(<PlanningIntentComposer />)

    expect(screen.getByRole('button', { name: /Planejando/ })).toBeDisabled()
    expect(screen.getByLabelText('O que você quer aprender?')).toBeDisabled()
  })

  it('shows a visible error message when starting the planning session fails', () => {
    useStartPlanningActionMock.mockReturnValue({
      error: new Error('network down'),
      isPending: false,
      startPlanning: startPlanningMock,
    })
    render(<PlanningIntentComposer />)

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Não foi possível iniciar o planejamento agora. Tente novamente.',
    )
  })

  it('discards any typed intent once the composer is remounted, such as after a reload (CA-08)', () => {
    const { unmount } = render(<PlanningIntentComposer />)
    fireEvent.change(screen.getByLabelText('O que você quer aprender?'), {
      target: { value: 'texto não enviado' },
    })
    expect(screen.getByLabelText('O que você quer aprender?')).toHaveValue(
      'texto não enviado',
    )
    unmount()

    render(<PlanningIntentComposer />)
    expect(screen.getByLabelText('O que você quer aprender?')).toHaveValue('')
  })

  describe('quota', () => {
    it('disables the field and pauses the primary action behind the blocked card when the quota is exhausted', () => {
      mockQuotaReading(true)
      render(<PlanningIntentComposer />)

      expect(screen.getByRole('status')).toHaveTextContent(BLOCKED_MESSAGE)
      expect(screen.getByRole('link', { name: 'Ver uso da IA' })).toHaveAttribute(
        'href',
        ROUTES.accountAiUsage,
      )
      expect(screen.getByLabelText('O que você quer aprender?')).toBeDisabled()
      const action = screen.getByRole('button', { name: 'Planejar com IA' })
      expect(action).toHaveAttribute('aria-disabled', 'true')
      expect(action).toBeEnabled()
      expect(action).toHaveAccessibleDescription(expect.stringContaining(BLOCKED_MESSAGE))
      action.focus()
      expect(action).toHaveFocus()
    })

    it('places the blocked card between the field and the actions and drops the glow frame', () => {
      mockQuotaReading(true)
      const { container } = render(<PlanningIntentComposer />)

      const field = screen.getByLabelText('O que você quer aprender?')
      const card = screen.getByRole('status')
      const action = screen.getByRole('button', { name: 'Planejar com IA' })
      expect(field.compareDocumentPosition(card)).toBe(Node.DOCUMENT_POSITION_FOLLOWING)
      expect(card.compareDocumentPosition(action)).toBe(Node.DOCUMENT_POSITION_FOLLOWING)
      expect(container.querySelector('.border-glow')).toBeNull()
    })

    it('keeps the glow frame while the quota is open', () => {
      mockQuotaReading(false)
      const { container } = render(<PlanningIntentComposer />)

      expect(container.querySelector('.border-glow')).not.toBeNull()
      expect(screen.queryByRole('status')).not.toBeInTheDocument()
    })

    it('ignores the blocked action without validation noise or a request and keeps manual creation', () => {
      mockQuotaReading(true)
      render(<PlanningIntentComposer />)

      fireEvent.click(screen.getByRole('button', { name: 'Planejar com IA' }))

      expect(startPlanningMock).not.toHaveBeenCalled()
      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
      expect(screen.getByRole('link', { name: 'Criar manualmente' })).toHaveAttribute(
        'href',
        ROUTES.learningGoalsNew,
      )
    })

    it('shows the blocked card, not the generic error, after the server refuses the start', () => {
      useStartPlanningActionMock.mockReturnValue({
        error: new PlanningRequestError({ kind: 'quota-exhausted' }),
        isPending: false,
        startPlanning: startPlanningMock,
      })
      render(<PlanningIntentComposer />)

      expect(useAiQuotaBlockMock).toHaveBeenCalledWith(true)
      expect(screen.getByRole('alert')).toHaveTextContent(BLOCKED_MESSAGE)
      expect(
        screen.queryByText(
          'Não foi possível iniciar o planejamento agora. Tente novamente.',
        ),
      ).not.toBeInTheDocument()
      expect(screen.getByLabelText('O que você quer aprender?')).toBeDisabled()
      expect(screen.getByRole('button', { name: 'Planejar com IA' })).toHaveAttribute(
        'aria-disabled',
        'true',
      )
    })

    it('keeps other start failures on the generic error with the primary action active', () => {
      useStartPlanningActionMock.mockReturnValue({
        error: new PlanningRequestError({ kind: 'unavailable' }),
        isPending: false,
        startPlanning: startPlanningMock,
      })
      render(<PlanningIntentComposer />)

      expect(useAiQuotaBlockMock).toHaveBeenCalledWith(false)
      expect(screen.getByRole('alert')).toHaveTextContent(
        'Não foi possível iniciar o planejamento agora. Tente novamente.',
      )
      expect(screen.getByRole('button', { name: 'Planejar com IA' })).not.toHaveAttribute(
        'aria-disabled',
      )
    })
  })
})
