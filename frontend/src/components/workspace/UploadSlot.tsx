import { useId, useRef, useState } from 'react'

import type { LabelView } from '../../types/app'
import { useI18n } from '../../i18n/I18nContext'

import { CameraCapture } from './CameraCapture'

interface UploadSlotProps {
  view: LabelView
  title: string
  file: File | null
  previewUrl: string | null
  onSelect: (file: File) => void
  onClear: () => void
}

export function UploadSlot({
  title,
  file,
  previewUrl,
  onSelect,
  onClear,
}: UploadSlotProps) {
  const { t } = useI18n()
  const id = useId()
  const inputRef = useRef<HTMLInputElement>(null)
  const [cameraOpen, setCameraOpen] = useState(false)

  return (
    <article className="drop-slot">
      <header>
        <h3>{title}</h3>

        {file ? (
          <button
            type="button"
            className="text-btn"
            onClick={onClear}
          >
            {t('remove')}
          </button>
        ) : null}
      </header>

      <label
        htmlFor={id}
        className={previewUrl ? 'drop-area has-image' : 'drop-area'}
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault()

          const next = event.dataTransfer.files[0]

          if (next) {
            onSelect(next)
          }
        }}
      >
        {previewUrl ? (
          <img
            src={previewUrl}
            alt={`${title} ${t('labelPreview')}`}
          />
        ) : (
          <span>
            {t('dropLabel')}
            <small>JPG / PNG</small>
          </span>
        )}
      </label>

      {/* Normal file picker */}
      <input
        ref={inputRef}
        id={id}
        className="sr-only"
        type="file"
        accept=".jpg,.jpeg,.png,image/jpeg,image/png"
        onChange={(event) => {
          const next = event.target.files?.[0]

          if (next) {
            onSelect(next)
          }

          event.target.value = ''
        }}
      />

      {!file ? (
        <div className="upload-actions">
          <button
            type="button"
            className="text-btn"
            onClick={() => inputRef.current?.click()}
          >
            {t('browse')}
          </button>

          <button
            type="button"
            className="camera-btn"
            onClick={() => setCameraOpen(true)}
          >
            {t('useCamera')}
          </button>
        </div>
      ) : (
        <div className="upload-actions">
          <p className="file-meta">{file.name}</p>

          <button
            type="button"
            className="text-btn"
            onClick={() => setCameraOpen(true)}
          >
            {t('retake')}
          </button>
        </div>
      )}
      {cameraOpen ? (
        <CameraCapture
          label={title}
          onCapture={(capturedFile) => {
            setCameraOpen(false)
            onSelect(capturedFile)
          }}
          onClose={() => setCameraOpen(false)}
        />
      ) : null}
    </article>
  )
}
