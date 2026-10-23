import type { XpHistoryEntry } from '@/core/gamification/xp-history'

import { XpHistoryRow } from './xp-history-row'

type XpHistoryTableProps = {
  entries: XpHistoryEntry[]
}

export const XpHistoryTable = ({ entries }: XpHistoryTableProps) => {
  return (
    <section
      aria-label='Registros de XP'
      className='rounded-[14px] border border-border bg-card'
    >
      {/* Decorative column headers: every value is announced from its own row,
          so the header row is hidden from assistive technology. */}
      <div
        aria-hidden='true'
        className='hidden border-b border-border px-6 py-4 text-xs text-muted-foreground sm:flex sm:gap-6'
      >
        <span className='w-9 shrink-0' />
        <span className='flex-1'>Origem</span>
        <span className='w-[164px]'>Concedido em</span>
        <span className='sm:text-right'>XP recebido</span>
      </div>

      <ul>
        {entries.map((entry) => (
          <XpHistoryRow entry={entry} key={entry.id} />
        ))}
      </ul>
    </section>
  )
}
