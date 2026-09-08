import { useMemo, useState } from 'react'

import type { CodeScan, VisualBox } from '../../types/compliance'

interface VisualBoxOverlayProps {
  src: string
  boxes: Record<string, VisualBox>
  codeScan?: CodeScan
  className?: string
}

function getPolygon(box: VisualBox): [number, number][] {
  if (box.polygon && box.polygon.length >= 3) {
    return box.polygon
  }

  if (box.box && box.box.length === 4) {
    const [x1, y1, x2, y2] = box.box

    return [
      [x1, y1],
      [x2, y1],
      [x2, y2],
      [x1, y2],
    ]
  }

  return []
}

function confidenceLabel(value: number) {
  if (value >= 0.9) return 'HIGH'
  if (value >= 0.7) return 'MEDIUM'
  return 'LOW'
}

export function VisualBoxOverlay({
  src,
  boxes,
  codeScan,
  className = '',
}: VisualBoxOverlayProps) {
  const [dimensions, setDimensions] = useState({
    width: 0,
    height: 0,
  })

  const validBoxes = useMemo(
    () =>
      Object.entries(boxes)
        .map(([field, value]) => ({
          field,
          value,
          polygon: getPolygon(value),
        }))
        .filter((item) => item.polygon.length >= 3),
    [boxes],
  )

  const qrCodes = codeScan?.qr_codes ?? []
  const barcodes = codeScan?.barcodes ?? []

  const codeOverlays = useMemo(
    () => [
      ...qrCodes
        .filter((code) => code.polygon && code.polygon.length >= 3)
        .map((code, index) => ({
          key: `qr-${index}-${code.data}`,
          type: 'QR',
          data: code.data,
          polygon: code.polygon,
        })),
      ...barcodes
        .filter((code) => code.polygon && code.polygon.length >= 3)
        .map((code, index) => ({
          key: `barcode-${index}-${code.data}`,
          type: 'BARCODE',
          data: code.data,
          polygon: code.polygon as [number, number][],
        })),
    ],
    [qrCodes, barcodes],
  )

  return (
    <div className={`visual-box-container ${className}`}>
      <svg
        className="visual-box-svg"
        viewBox={
          dimensions.width && dimensions.height
            ? `0 0 ${dimensions.width} ${dimensions.height}`
            : undefined
        }
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label="OCR fields and code detection overlay"
      >
        <image
          href={src}
          x="0"
          y="0"
          width={dimensions.width || undefined}
          height={dimensions.height || undefined}
          preserveAspectRatio="xMidYMid meet"
          onLoad={() => {
            const image = new Image()

            image.onload = () => {
              setDimensions({
                width: image.naturalWidth,
                height: image.naturalHeight,
              })
            }

            image.src = src
          }}
        />

        {dimensions.width > 0 &&
          dimensions.height > 0 &&
          validBoxes.map(({ field, value, polygon }) => {
            const points = polygon
              .map(([x, y]) => `${x},${y}`)
              .join(' ')

            const labelX = Math.min(...polygon.map(([x]) => x))

            const labelY = Math.max(
              18,
              Math.min(...polygon.map(([, y]) => y)) - 8,
            )

            return (
              <g
                key={`${field}-${value.text}`}
                className="visual-field-group"
              >
                <polygon
                  points={points}
                  className="visual-field-polygon"
                />

                <text
                  x={labelX}
                  y={labelY}
                  className="visual-field-label-svg"
                >
                  {field.replaceAll('_', ' ')}
                </text>
              </g>
            )
          })}

        {dimensions.width > 0 &&
          dimensions.height > 0 &&
          codeOverlays.map(({ key, type, data, polygon }) => {
            const points = polygon
              .map(([x, y]) => `${x},${y}`)
              .join(' ')

            const labelX = Math.min(...polygon.map(([x]) => x))

            const labelY = Math.max(
              18,
              Math.min(...polygon.map(([, y]) => y)) - 10,
            )

            return (
              <g key={key} className="visual-code-group">
                <polygon
                  points={points}
                  className="visual-code-polygon"
                />

                <text
                  x={labelX}
                  y={labelY}
                  className="visual-code-label-svg"
                >
                  {type}
                </text>

                <title>
                  {type}: {data}
                </title>
              </g>
            )
          })}
      </svg>

      {validBoxes.length > 0 || codeOverlays.length > 0 ? (
        <div className="visual-box-legend">
          {validBoxes.length > 0 && (
            <>
              <span>
                {validBoxes.length} field
                {validBoxes.length === 1 ? '' : 's'} detected
              </span>

              <span className="visual-confidence">
                {confidenceLabel(
                  Math.max(
                    ...validBoxes.map(
                      ({ value }) => value.confidence,
                    ),
                  ),
                )}{' '}
                confidence
              </span>
            </>
          )}

          {codeOverlays.length > 0 && (
            <span className="visual-code-legend">
              {codeOverlays.length} code
              {codeOverlays.length === 1 ? '' : 's'} detected
            </span>
          )}
        </div>
      ) : null}
    </div>
  )
}
