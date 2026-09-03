import { useId, useRef } from 'react'
import type { LabelView } from '../../types/app'

interface UploadSlotProps {
  view: LabelView
  title: string
  file: File | null
  previewUrl: string | null
  onSelect: (file: File) => void
  onClear: () => void
}

export function UploadSlot({
  view,
  title,
  file,
  previewUrl,
  onSelect,
  onClear,
}: UploadSlotProps) {
  const id = useId()
  const inputRef = useRef<HTMLInputElement>(null)

  return (
    <article className="drop-slot">
      <header>
        <h3>{title}</h3>
        {file ? (
          <button type="button" className="text-btn" onClick={onClear}>
            Remove
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
          if (next) onSelect(next)
        }}
      >
        {previewUrl ? (
          <img src={previewUrl} alt={`${view} label preview`} />
        ) : (
          <span>
            Drop {view} label
            <small>JPG / PNG</small>
          </span>
        )}
      </label>
      <input
        ref={inputRef}
        id={id}
        className="sr-only"
        type="file"
        accept=".jpg,.jpeg,.png,image/jpeg,image/png"
        onChange={(event) => {
          const next = event.target.files?.[0]
          if (next) onSelect(next)
          event.target.value = ''
        }}
      />
      {!file ? (
        <button
          type="button"
          className="text-btn"
          onClick={() => inputRef.current?.click()}
        >
          Replace / browse
        </button>
      ) : (
        <p className="file-meta">{file.name}</p>
      )}
    </article>
  )
}
