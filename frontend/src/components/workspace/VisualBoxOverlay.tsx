import { useMemo, useState } from 'react'

import type { VisualBox } from '../../types/compliance'

interface VisualBoxOverlayProps {
  src: string
  boxes: Record<string, VisualBox>
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
        aria-label="OCR field detection overlay"
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
            const points = polygon.map(([x, y]) => `${x},${y}`).join(' ')

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
      </svg>

      {validBoxes.length > 0 ? (
        <div className="visual-box-legend">
          <span>
            {validBoxes.length} field{validBoxes.length === 1 ? '' : 's'} detected
          </span>

          <span className="visual-confidence">
            {confidenceLabel(
              Math.max(...validBoxes.map(({ value }) => value.confidence)),
            )}{' '}
            confidence
          </span>
        </div>
      ) : null}
    </div>
  )
}
