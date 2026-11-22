// Application boundary for user-visible toasts (see the UI catch-block rule).
//
// Feature code calls these functions only. They are the one place that knows about
// Sonner, and the root layout owns the single `Toaster` mount.
import { toast } from 'sonner'

export function showErrorToast(message: string) {
  toast.error(message)
}

export function showWarningToast(message: string) {
  toast.warning(message)
}

export function showInfoToast(message: string) {
  toast.info(message)
}
