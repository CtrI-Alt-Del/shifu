import type { PairMatchingItem } from './choice-activity'

/** The text of an item by key, or the key itself when the item is unknown. */
export function pairMatchingItemText(
  items: readonly PairMatchingItem[] | undefined,
  key: string,
): string {
  return items?.find((item) => item.key === key)?.text ?? key
}
