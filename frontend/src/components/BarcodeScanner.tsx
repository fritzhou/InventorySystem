import { useEffect, useRef, useState, type FormEvent } from 'react'

interface DetectedBarcode { rawValue: string }
interface BarcodeDetectorInstance { detect: (source: HTMLVideoElement) => Promise<DetectedBarcode[]> }
interface BarcodeDetectorConstructor {
  new(options: { formats: string[] }): BarcodeDetectorInstance
  getSupportedFormats?: () => Promise<string[]>
}

declare global { interface Window { BarcodeDetector?: BarcodeDetectorConstructor } }

interface BarcodeScannerProps { onDetected: (barcode: string) => void }

const formats = ['ean_13', 'ean_8', 'upc_a', 'upc_e', 'code_128']

export function BarcodeScanner({ onDetected }: BarcodeScannerProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const detectedRef = useRef(false)
  const [state, setState] = useState<'loading' | 'ready' | 'denied' | 'unavailable'>('loading')
  const [manualBarcode, setManualBarcode] = useState('')

  useEffect(() => {
    let stream: MediaStream | null = null
    let frame = 0
    let cancelled = false

    const stop = () => {
      cancelled = true
      cancelAnimationFrame(frame)
      stream?.getTracks().forEach((track) => track.stop())
    }

    const start = async () => {
      if (!navigator.mediaDevices?.getUserMedia || !window.BarcodeDetector) {
        setState('unavailable')
        return
      }
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' } }, audio: false })
        if (cancelled) { stream.getTracks().forEach((track) => track.stop()); return }
        const video = videoRef.current
        if (!video) return
        video.srcObject = stream
        await video.play()
        if (cancelled) return
        const supported = window.BarcodeDetector.getSupportedFormats
          ? await window.BarcodeDetector.getSupportedFormats()
          : formats
        const detector = new window.BarcodeDetector({ formats: formats.filter((format) => supported.includes(format)) })
        setState('ready')
        const scan = async () => {
          if (cancelled || detectedRef.current) return
          try {
            const [result] = await detector.detect(video)
            const barcode = result?.rawValue.trim()
            if (barcode && !detectedRef.current) {
              detectedRef.current = true
              stop()
              onDetected(barcode)
              return
            }
          } catch { /* A frame may be unreadable while the camera is focusing. */ }
          frame = requestAnimationFrame(scan)
        }
        frame = requestAnimationFrame(scan)
      } catch (error) {
        if (cancelled) return
        const denied = error instanceof DOMException && (error.name === 'NotAllowedError' || error.name === 'SecurityError')
        setState(denied ? 'denied' : 'unavailable')
      }
    }

    void start()
    return stop
  }, [onDetected])

  const submitManual = (event: FormEvent) => {
    event.preventDefault()
    const barcode = manualBarcode.trim()
    if (!barcode || detectedRef.current) return
    detectedRef.current = true
    onDetected(barcode)
  }

  return <div className="scanner">
    <div className="camera-preview">
      <video ref={videoRef} muted playsInline aria-label="Live barcode camera preview" />
      {state === 'loading' && <p role="status">Starting camera…</p>}
      {state === 'ready' && <div className="scan-guide" aria-hidden="true" />}
      {state === 'denied' && <p className="camera-message" role="alert"><strong>Camera permission denied</strong><span>Allow camera access in your browser settings, then retry.</span></p>}
      {state === 'unavailable' && <p className="camera-message" role="alert"><strong>Camera unavailable</strong><span>This browser or device cannot start barcode scanning. Use manual entry below.</span></p>}
    </div>
    <p className="privacy-note">Camera frames are processed locally in your browser and are never uploaded or stored.</p>
    <form className="manual-scan" onSubmit={submitManual}>
      <label htmlFor="manual-barcode">Enter barcode manually</label>
      <div><input id="manual-barcode" inputMode="numeric" autoComplete="off" value={manualBarcode} onChange={(event) => setManualBarcode(event.target.value)} placeholder="EAN, UPC, or Code 128" /><button className="button secondary">Look up</button></div>
    </form>
  </div>
}
