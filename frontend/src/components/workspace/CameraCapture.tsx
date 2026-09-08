import { useEffect, useRef, useState } from 'react'

import { useI18n } from '../../i18n/I18nContext'

interface CameraCaptureProps {
  label: string
  onCapture: (file: File) => void
  onClose: () => void
}

type QualityState = {
  status: 'GOOD' | 'WARNING'
  messages: string[]
}

function evaluateFrame(
  canvas: HTMLCanvasElement,
): QualityState {
  const sampleWidth = 480
  const sampleHeight = Math.max(
    270,
    Math.round(
      (canvas.height / canvas.width) * sampleWidth,
    ),
  )

  const sampleCanvas = document.createElement('canvas')
  sampleCanvas.width = sampleWidth
  sampleCanvas.height = sampleHeight

  const sampleContext = sampleCanvas.getContext('2d', {
    willReadFrequently: true,
  })

  if (!sampleContext) {
    return {
      status: 'WARNING',
      messages: ['Unable to evaluate image quality.'],
    }
  }

  sampleContext.drawImage(
    canvas,
    0,
    0,
    sampleWidth,
    sampleHeight,
  )

  const imageData = sampleContext.getImageData(
    0,
    0,
    sampleWidth,
    sampleHeight,
  )

  const pixels = imageData.data

  let brightnessSum = 0
  let brightPixels = 0

  const grayValues = new Float32Array(
    sampleWidth * sampleHeight,
  )

  for (let i = 0, pixel = 0; i < pixels.length; i += 4, pixel++) {
    const r = pixels[i]
    const g = pixels[i + 1]
    const b = pixels[i + 2]

    const brightness =
      0.299 * r +
      0.587 * g +
      0.114 * b

    grayValues[pixel] = brightness
    brightnessSum += brightness

    /*
     * Potential glare:
     * very bright + low colour saturation.
     */
    const maxChannel = Math.max(r, g, b)
    const minChannel = Math.min(r, g, b)

    if (
      maxChannel >= 245 &&
      maxChannel - minChannel <= 18
    ) {
      brightPixels += 1
    }
  }

  const totalPixels = sampleWidth * sampleHeight
  const meanBrightness = brightnessSum / totalPixels
  const glareRatio = brightPixels / totalPixels

  /*
   * Simple Laplacian-variance blur estimate.
   *
   * We calculate horizontal and vertical second differences
   * over the grayscale sample. Higher variance generally means
   * more edge detail and therefore a sharper frame.
   */
  let laplacianSum = 0
  let laplacianSquaredSum = 0
  let laplacianCount = 0

  for (let y = 1; y < sampleHeight - 1; y += 1) {
    for (let x = 1; x < sampleWidth - 1; x += 1) {
      const index =
        y * sampleWidth + x

      const center = grayValues[index]

      const left =
        grayValues[index - 1]

      const right =
        grayValues[index + 1]

      const top =
        grayValues[index - sampleWidth]

      const bottom =
        grayValues[index + sampleWidth]

      const laplacian =
        left +
        right +
        top +
        bottom -
        4 * center

      laplacianSum += laplacian
      laplacianSquaredSum += laplacian * laplacian
      laplacianCount += 1
    }
  }

  const laplacianMean =
    laplacianCount > 0
      ? laplacianSum / laplacianCount
      : 0

  const blurScore =
    laplacianCount > 0
      ? laplacianSquaredSum / laplacianCount -
        laplacianMean * laplacianMean
      : 0

  const messages: string[] = []

  if (blurScore < 35) {
    messages.push('Hold steady — image looks blurry.')
  }

  if (meanBrightness < 60) {
    messages.push('Too dark — move to better lighting.')
  } else if (meanBrightness > 220) {
    messages.push('Too bright — reduce direct light.')
  }

  if (glareRatio > 0.025) {
    messages.push('Glare detected — tilt the product slightly.')
  }

  return {
    status: messages.length === 0 ? 'GOOD' : 'WARNING',
    messages,
  }
}

export function CameraCapture({
  label,
  onCapture,
  onClose,
}: CameraCaptureProps) {
  const { t } = useI18n()

  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const qualityCanvasRef = useRef<HTMLCanvasElement>(null)
  const lastQualityCheckRef = useRef(0)

  const [error, setError] = useState<string | null>(null)
  const [isReady, setIsReady] = useState(false)

  const [quality, setQuality] = useState<QualityState>({
    status: 'WARNING',
    messages: [t('cameraCapture') + '…'],
  })

  useEffect(() => {
    let cancelled = false

    async function startCamera() {
      try {
        if (
          !navigator.mediaDevices ||
          !navigator.mediaDevices.getUserMedia
        ) {
          throw new Error('Camera API unavailable')
        }

        const stream =
          await navigator.mediaDevices.getUserMedia({
            video: {
              facingMode: {
                ideal: 'environment',
              },
              width: {
                ideal: 1920,
              },
              height: {
                ideal: 1080,
              },
            },
            audio: false,
          })

        if (cancelled) {
          stream
            .getTracks()
            .forEach((track) => track.stop())
          return
        }

        streamRef.current = stream

        const video = videoRef.current

        if (!video) return

        video.srcObject = stream
        await video.play()

        if (!cancelled) {
          setIsReady(true)
        }
      } catch (err) {
        console.error('Camera access failed:', err)

        setError(
          err instanceof DOMException &&
            err.name === 'NotAllowedError'
            ? 'Camera permission was denied. Please allow camera access and try again.'
            : 'Could not access the camera on this device.',
        )
      }
    }

    startCamera()

    return () => {
      cancelled = true

      streamRef.current
        ?.getTracks()
        .forEach((track) => track.stop())

      streamRef.current = null
    }
  }, [])

  useEffect(() => {
    if (!isReady) return

    let animationFrame = 0
    let cancelled = false

    function inspectFrame(timestamp: number) {
      if (cancelled) return

      const video = videoRef.current

      if (
        !video ||
        video.videoWidth === 0 ||
        video.videoHeight === 0
      ) {
        animationFrame = requestAnimationFrame(inspectFrame)
        return
      }

      /*
       * Don't perform image analysis on every animation frame.
       * 500 ms is enough for live guidance and keeps the phone CPU
       * load reasonable.
       */
      if (
        timestamp -
          lastQualityCheckRef.current >=
        500
      ) {
        lastQualityCheckRef.current = timestamp

        const canvas =
          qualityCanvasRef.current ??
          document.createElement('canvas')

        canvas.width = 480
        canvas.height = Math.max(
          270,
          Math.round(
            (video.videoHeight /
              video.videoWidth) *
              480,
          ),
        )

        const context = canvas.getContext('2d', {
          willReadFrequently: true,
        })

        if (context) {
          context.drawImage(
            video,
            0,
            0,
            canvas.width,
            canvas.height,
          )

          setQuality(
            evaluateFrame(canvas),
          )
        }
      }

      animationFrame =
        requestAnimationFrame(inspectFrame)
    }

    animationFrame =
      requestAnimationFrame(inspectFrame)

    return () => {
      cancelled = true
      cancelAnimationFrame(animationFrame)
    }
  }, [isReady])

  function handleCapture() {
    const video = videoRef.current

    if (
      !video ||
      video.videoWidth === 0 ||
      video.videoHeight === 0
    ) {
      return
    }

    const canvas = document.createElement('canvas')

    canvas.width = video.videoWidth
    canvas.height = video.videoHeight

    const context = canvas.getContext('2d')

    if (!context) {
      setError(t('captureFrameFailed'))
      return
    }

    context.drawImage(
      video,
      0,
      0,
      canvas.width,
      canvas.height,
    )

    canvas.toBlob(
      (blob) => {
        if (!blob) {
          setError(t('captureImageFailed'))
          return
        }

        const timestamp = new Date()
          .toISOString()
          .replace(/[:.]/g, '-')

        const file = new File(
          [blob],
          `label-lens-${label.toLowerCase()}-${timestamp}.jpg`,
          {
            type: 'image/jpeg',
          },
        )

        onCapture(file)
      },
      'image/jpeg',
      0.92,
    )
  }

  return (
    <div className="camera-modal-backdrop">
      <div
        className="camera-modal"
        role="dialog"
        aria-modal="true"
        aria-label={`${label} camera`}
      >
        <header className="camera-modal-header">
          <div>
            <p className="section-index">
              {t('cameraCapture')}
            </p>

            <h2>{label} label</h2>
          </div>

          <button
            type="button"
            className="text-btn"
            onClick={onClose}
          >
            {t('cameraClose')}
          </button>
        </header>

        {error ? (
          <div
            className="camera-error"
            role="alert"
          >
            <p>{error}</p>

            <button
              type="button"
              className="text-btn"
              onClick={onClose}
            >
              {t('cameraBack')}
            </button>
          </div>
        ) : (
          <>
            <div className="camera-preview">
              <video
                ref={videoRef}
                className="camera-video"
                playsInline
                muted
              />

              <div className="camera-guide">
                <div className="camera-guide-frame" />

                <p>
                  {t('alignLabel')}
                </p>
              </div>

              <div
                className={`camera-quality ${
                  quality.status === 'GOOD'
                    ? 'is-good'
                    : 'is-warning'
                }`}
                role="status"
                aria-live="polite"
              >
                {quality.status === 'GOOD' ? (
                  <>
                    <span className="camera-quality-icon">
                      ✓
                    </span>
                    <span>
                      {t('goodToScan')}
                    </span>
                  </>
                ) : (
                  <>
                    <span className="camera-quality-icon">
                      !
                    </span>

                    <span>
                      {quality.messages[0] ??
                        t('improveImageQuality')}
                    </span>
                  </>
                )}
              </div>
            </div>

            <div className="camera-controls">
              {quality.messages.length > 0 && (
                <div className="camera-quality-details">
                  {quality.messages.map(
                    (message) => (
                      <span key={message}>
                        {message}
                      </span>
                    ),
                  )}
                </div>
              )}

              <button
                type="button"
                className="camera-capture-btn"
                disabled={!isReady}
                onClick={handleCapture}
                aria-label={`${t('captureLabel')} ${label}`}
              >
                <span className="camera-shutter" />
              </button>
            </div>

            <canvas
              ref={qualityCanvasRef}
              className="sr-only"
              aria-hidden="true"
            />
          </>
        )}
      </div>
    </div>
  )
}
