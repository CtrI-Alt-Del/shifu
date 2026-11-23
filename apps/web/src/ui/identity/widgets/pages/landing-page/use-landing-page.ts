import { useEffect, useState } from 'react'

export function useLandingPage() {
  const [isDocumentVisible, setIsDocumentVisible] = useState(false)

  useEffect(() => {
    function handleVisibilityChange() {
      setIsDocumentVisible(document.visibilityState === 'visible')
    }

    handleVisibilityChange()
    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [])

  return { isDocumentVisible }
}
