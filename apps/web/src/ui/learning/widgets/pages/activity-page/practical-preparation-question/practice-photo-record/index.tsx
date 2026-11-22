import { PRACTICE_PHOTO_ACCEPT_ATTRIBUTE } from '@/core/learning/practice-photo-rules'
import { Button } from '@/ui/shadcn/button'
import { Icon } from '@/ui/shared/widgets/components/icon'

import type { PracticeRecordView } from '../use-practical-preparation-question'
import { usePracticePhotoRecord } from './use-practice-photo-record'

export type PracticePhotoRecordProps = {
  view: PracticeRecordView
  position: number
  isDisabled: boolean
  onSelectPhoto: (recordKey: string, file: File) => void
  onRetryPhoto: (recordKey: string) => void
  onRemovePhoto: (recordKey: string) => void
}

export const PracticePhotoRecord = ({
  isDisabled,
  onRemovePhoto,
  onRetryPhoto,
  onSelectPhoto,
  position,
  view,
}: PracticePhotoRecordProps) => {
  const { record, status, thumbnailUrl, fileName, meta, message, canRetry } = view
  const { inputRef, handleChoosePhoto, handleChangeFile } = usePracticePhotoRecord({
    recordKey: record.key,
    onSelectPhoto,
  })
  const isBusy = status === 'uploading' || status === 'removing'
  const hasPhoto = thumbnailUrl !== null
  const isLocked = isDisabled || isBusy

  return (
    <li className='space-y-3 border-b border-border pb-5 last:border-b-0 last:pb-0'>
      <div className='flex items-center justify-between gap-3'>
        <h3 className='font-medium text-foreground'>
          {position}. {record.label}
        </h3>
        {status === 'ready' ? (
          <Icon className='shrink-0 text-success' name='circle-check' size={18} />
        ) : (
          <span className='text-xs text-muted-foreground'>Obrigatória</span>
        )}
      </div>

      <input
        accept={PRACTICE_PHOTO_ACCEPT_ATTRIBUTE}
        aria-hidden='true'
        className='sr-only'
        disabled={isLocked}
        onChange={handleChangeFile}
        ref={inputRef}
        tabIndex={-1}
        type='file'
      />

      {hasPhoto && !isBusy ? (
        <div className='flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4'>
          <div className='flex min-w-0 flex-1 items-center gap-4'>
            <img
              alt={`Foto do registro: ${record.label}`}
              className='h-[76px] w-[104px] shrink-0 rounded-md border border-border object-cover'
              height={76}
              src={thumbnailUrl}
              width={104}
            />
            <div className='min-w-0 flex-1 space-y-1'>
              {meta ? <p className='truncate text-sm text-foreground'>{meta}</p> : null}
              <p className='flex items-center gap-1.5 text-sm text-success'>
                <Icon className='shrink-0' name='circle-check' size={14} />
                <output>Foto adicionada</output>
              </p>
            </div>
          </div>
          <div className='flex shrink-0 items-center gap-1'>
            <Button
              aria-label={`Trocar foto: ${record.label}`}
              disabled={isLocked}
              onClick={handleChoosePhoto}
              type='button'
              variant='outline'
            >
              Trocar foto
            </Button>
            <Button
              aria-label={`Remover foto: ${record.label}`}
              className='size-11 px-0'
              disabled={isLocked}
              onClick={() => onRemovePhoto(record.key)}
              type='button'
              variant='ghost'
            >
              <Icon name='x' size={18} />
            </Button>
          </div>
        </div>
      ) : null}

      {status === 'missing' ? (
        <>
          <Button
            aria-label={`Adicionar foto: ${record.label}`}
            className='w-full'
            disabled={isLocked}
            onClick={handleChoosePhoto}
            type='button'
            variant='outline'
          >
            <Icon className='mr-2' name='camera' size={16} />
            Adicionar foto
          </Button>
          <p className='text-xs text-muted-foreground'>Mostre: {record.mustShow}</p>
        </>
      ) : null}

      {isBusy ? (
        <div className='space-y-2'>
          <p className='flex items-center gap-2 text-sm text-foreground'>
            <Icon
              className='shrink-0 text-muted-foreground motion-safe:animate-spin'
              name='loader-circle'
              size={16}
            />
            <span className='truncate'>{fileName ?? record.label}</span>
          </p>
          <div
            aria-hidden='true'
            className='h-1 w-full overflow-hidden rounded-full bg-muted'
          >
            <div className='h-full w-1/2 rounded-full bg-success motion-safe:animate-pulse' />
          </div>
          <output className='block text-xs text-muted-foreground'>
            {status === 'removing' ? 'Removendo foto…' : 'Adicionando foto…'}
          </output>
        </div>
      ) : null}

      {status === 'failed' && !hasPhoto ? (
        <div className='space-y-3'>
          <p className='flex items-start gap-2 text-sm text-selo-text' role='alert'>
            <Icon className='mt-0.5 shrink-0' name='triangle-alert' size={16} />
            <span>{message ?? 'Não foi possível adicionar esta foto.'}</span>
          </p>
          {fileName ? (
            <p className='truncate text-xs text-muted-foreground'>{fileName}</p>
          ) : null}
          <div className='flex flex-wrap gap-2'>
            {canRetry ? (
              <Button
                aria-label={`Tentar enviar novamente: ${record.label}`}
                className='flex-1'
                disabled={isLocked}
                onClick={() => onRetryPhoto(record.key)}
                type='button'
                variant='outline'
              >
                Tentar novamente
              </Button>
            ) : null}
            <Button
              aria-label={`Escolher outra foto: ${record.label}`}
              className='flex-1'
              disabled={isLocked}
              onClick={handleChoosePhoto}
              type='button'
              variant='outline'
            >
              Escolher outra foto
            </Button>
          </div>
        </div>
      ) : null}

      {hasPhoto && !isBusy && message ? (
        <div className='space-y-2'>
          <p className='flex items-start gap-2 text-sm text-selo-text' role='alert'>
            <Icon className='mt-0.5 shrink-0' name='triangle-alert' size={16} />
            <span>{message}</span>
          </p>
          {canRetry ? (
            <Button
              aria-label={`Tentar enviar novamente: ${record.label}`}
              disabled={isLocked}
              onClick={() => onRetryPhoto(record.key)}
              type='button'
              variant='outline'
            >
              Tentar novamente
            </Button>
          ) : null}
        </div>
      ) : null}
    </li>
  )
}
