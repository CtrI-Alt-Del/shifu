import { type ChangeEvent, useRef } from 'react'

export type UsePracticePhotoRecordProps = {
  recordKey: string
  onSelectPhoto: (recordKey: string, file: File) => void
}

export function usePracticePhotoRecord({
  onSelectPhoto,
  recordKey,
}: UsePracticePhotoRecordProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  function handleChoosePhoto() {
    inputRef.current?.click()
  }

  function handleChangeFile(event: ChangeEvent<HTMLInputElement>) {
    const [file] = Array.from(event.target.files ?? [])
    // Clearing the value lets the learner pick the same file again after a failure.
    event.target.value = ''
    if (file) onSelectPhoto(recordKey, file)
  }

  return { inputRef, handleChoosePhoto, handleChangeFile }
}
