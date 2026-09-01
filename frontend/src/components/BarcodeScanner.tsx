import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from 'react'

interface DetectedBarcode { rawValue: string }
interface BarcodeDetectorInstance { detect: (source: HTMLVideoElement) => Promise<DetectedBarcode[]> }
interface BarcodeDetectorConstructor {
  new(options: { formats: string[] }): BarcodeDetectorInstance
  getSupportedFormats?: () => Promise<string[]>
}

interface Html5QrcodeCamera { id: string; label: string }
interface Html5QrcodeInstance {
  start: (
    cameraIdOrConfig: string | MediaTrackConstraints,
    config: { fps?: number; aspectRatio?: number },
    onSuccess: (decodedText: string) => void,
    onError?: (errorMessage: string) => void,
  ) => Promise<null>
  stop: () => Promise<void>
  clear: () => void
  scanFile: (file: File, showImage?: boolean) => Promise<string>
}
interface Html5QrcodeConstructor {
  new(elementId: string, config?: { verbose?: boolean }): Html5QrcodeInstance
  getCameras: () => Promise<Html5QrcodeCamera[]>
}

declare global {
  interface Window {
    BarcodeDetector?: BarcodeDetectorConstructor
    Html5Qrcode?: Html5QrcodeConstructor
  }
}

interface BarcodeScannerProps { onDetected: (barcode: string) => void }

const formats = ['ean_13', 'ean_8', 'upc_a', 'upc_e', 'code_128']
const readerId = 'stockflow-barcode-reader'
const scannerSources = [
  'https://cdn.jsdelivr.net/npm/html5-qrcode@2.3.8/html5-qrcode.min.js',
  'https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js',
]
let scannerLibraryPromise: Promise<Html5QrcodeConstructor> | null = null

function loadScript(src: string, index: number): Promise<void> {
  return new Promise((resolve, reject) => {
    const id = `stockflow-html5-qrcode-${index}`
    const existing = document.getElementById(id) as HTMLScriptElement | null
    if (existing) {
      if (window.Html5Qrcode) { resolve(); return }
      existing.addEventListener('load', () => resolve(), { once: true })
      existing.addEventListener('error', () => reject(new Error('Scanner library failed to load')), { once: true })
      return
    }
    const script = document.createElement('script')
    script.id = id
    script.src = src
    script.async = true
    script.crossOrigin = 'anonymous'
    script.onload = () => resolve()
    script.onerror = () => { script.remove(); reject(new Error('Scanner library failed to load')) }
    document.head.appendChild(script)
  })
}

function loadHtml5Qrcode(): Promise<Html5QrcodeConstructor> {
  if (window.Html5Qrcode) return Promise.resolve(window.Html5Qrcode)
  if (!scannerLibraryPromise) {
    scannerLibraryPromise = (async () => {
      for (let index = 0; index < scannerSources.length; index += 1) {
        try {
          await loadScript(scannerSources[index], index)
          if (window.Html5Qrcode) return window.Html5Qrcode
        } catch { /* Try the next pinned CDN source. */ }
      }
      throw new Error('Barcode scanner compatibility library is unavailable')
    })().catch((error) => {
      scannerLibraryPromise = null
      throw error
    })
  }
  return scannerLibraryPromise
}

function permissionDenied(error: unknown) {
  if (error instanceof DOMException && (error.name === 'NotAllowedError' || error.name === 'SecurityError')) return true
  const message = String(error).toLowerCase()
  return message.includes('permission') || message.includes('notallowed') || message.includes('not allowed')
}

function preferredCamera(cameras: Html5QrcodeCamera[]) {
  return cameras.find((camera) => /back|rear|environment|world/i.test(camera.label)) ?? cameras[0]
}

export function BarcodeScanner({ onDetected }: BarcodeScannerProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const detectedRef = useRef(false)
  const compatScannerRef = useRef<Html5QrcodeInstance | null>(null)
  const nativeStreamRef = useRef<MediaStream | null>(null)
  const [state, setState] = useState<'loading' | 'ready' | 'denied' | 'unavailable'>('loading')
  const [engine, setEngine] = useState<'compat' | 'native' | null>(null)
  const [manualBarcode, setManualBarcode] = useState('')
  const [photoMessage, setPhotoMessage] = useState('')
  const [photoBusy, setPhotoBusy] = useState(false)

  useEffect(() => {
    let frame = 0
    let cancelled = false

    const stopNative = () => {
      cancelAnimationFrame(frame)
      nativeStreamRef.current?.getTracks().forEach((track) => track.stop())
      nativeStreamRef.current = null
    }

    const stopCompat = async () => {
      const scanner = compatScannerRef.current
      if (!scanner) return
      try { await scanner.stop() } catch { /* It may not have reached the scanning state. */ }
      try { scanner.clear() } catch { /* Ignore cleanup failures. */ }
      compatScannerRef.current = null
    }

    const finish = (value: string) => {
      const barcode = value.trim()
      if (!barcode || detectedRef.current || cancelled) return
      detectedRef.current = true
      stopNative()
      void stopCompat()
      onDetected(barcode)
    }

    const startNative = async () => {
      if (!navigator.mediaDevices?.getUserMedia || !window.BarcodeDetector) throw new Error('Native scanner unavailable')
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' } }, audio: false })
      nativeStreamRef.current = stream
      if (cancelled) { stopNative(); return }
      const video = videoRef.current
      if (!video) throw new Error('Camera preview unavailable')
      video.srcObject = stream
      await video.play()
      const supported = window.BarcodeDetector.getSupportedFormats
        ? await window.BarcodeDetector.getSupportedFormats()
        : formats
      const supportedFormats = formats.filter((format) => supported.includes(format))
      if (!supportedFormats.length) throw new Error('No supported barcode formats')
      const detector = new window.BarcodeDetector({ formats: supportedFormats })
      setEngine('native')
      setState('ready')
      const scan = async () => {
        if (cancelled || detectedRef.current) return
        try {
          const [result] = await detector.detect(video)
          if (result?.rawValue) { finish(result.rawValue); return }
        } catch { /* A camera frame may be unreadable while focusing. */ }
        frame = requestAnimationFrame(scan)
      }
      frame = requestAnimationFrame(scan)
    }

    const start = async () => {
      if (!navigator.mediaDevices?.getUserMedia) {
        setState('unavailable')
        return
      }

      try {
        const Html5Qrcode = await loadHtml5Qrcode()
        if (cancelled) return
        const cameras = await Html5Qrcode.getCameras()
        if (!cameras.length) throw new Error('No camera found')
        const scanner = new Html5Qrcode(readerId, { verbose: false })
        compatScannerRef.current = scanner
        setEngine('compat')
        await scanner.start(
          preferredCamera(cameras).id,
          { fps: 12, aspectRatio: 16 / 9 },
          finish,
          () => undefined,
        )
        if (cancelled) { await stopCompat(); return }
        setState('ready')
        return
      } catch (error) {
        await stopCompat()
        if (cancelled) return
        if (permissionDenied(error)) { setState('denied'); return }
      }

      try {
        await startNative()
      } catch (error) {
        stopNative()
        if (cancelled) return
        setState(permissionDenied(error) ? 'denied' : 'unavailable')
      }
    }

    void start()
    return () => {
      cancelled = true
      stopNative()
      void stopCompat()
    }
  }, [onDetected])

  const submitManual = (event: FormEvent) => {
    event.preventDefault()
    const barcode = manualBarcode.trim()
    if (!barcode || detectedRef.current) return
    detectedRef.current = true
    onDetected(barcode)
  }

  const scanPhoto = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file || detectedRef.current) return
    setPhotoBusy(true)
    setPhotoMessage('Scanning image…')
    try {
      const activeScanner = compatScannerRef.current
      if (activeScanner) {
        try { await activeScanner.stop() } catch { /* Ignore if already stopped. */ }
        try { activeScanner.clear() } catch { /* Ignore cleanup failures. */ }
        compatScannerRef.current = null
      }
      nativeStreamRef.current?.getTracks().forEach((track) => track.stop())
      nativeStreamRef.current = null

      const Html5Qrcode = await loadHtml5Qrcode()
      const scanner = new Html5Qrcode(readerId, { verbose: false })
      const decoded = await scanner.scanFile(file, false)
      try { scanner.clear() } catch { /* Ignore cleanup failures. */ }
      const barcode = decoded.trim()
      if (!barcode) throw new Error('No barcode found')
      detectedRef.current = true
      onDetected(barcode)
    } catch {
      setPhotoMessage('No readable barcode was found in that image. Try a clearer photo or enter it manually.')
      setState('unavailable')
    } finally {
      setPhotoBusy(false)
    }
  }

  return <div className="scanner">
    <div className={`camera-preview camera-engine-${engine ?? 'loading'}`}>
      <div id={readerId} className="compat-camera-preview" aria-label="Live barcode camera preview" />
      <video ref={videoRef} className="native-camera-preview" muted playsInline aria-label="Live barcode camera preview" />
      {state === 'loading' && <p role="status">Starting camera…</p>}
      {state === 'ready' && <div className="scan-guide" aria-hidden="true" />}
      {state === 'denied' && <p className="camera-message" role="alert"><strong>Camera permission denied</strong><span>Allow camera access for this site in your browser or operating-system privacy settings, then reopen the scanner.</span></p>}
      {state === 'unavailable' && <p className="camera-message" role="alert"><strong>Live camera unavailable</strong><span>You can still scan a barcode from a photo or enter the code manually below.</span></p>}
    </div>
    <p className="privacy-note">Camera frames and barcode photos are processed locally in your browser and are never uploaded or stored.</p>
    <div className="scanner-photo-fallback">
      <label className={`button secondary ${photoBusy ? 'disabled' : ''}`}>
        {photoBusy ? 'Scanning photo…' : 'Scan barcode from photo'}
        <input type="file" accept="image/*" capture="environment" onChange={(event) => void scanPhoto(event)} disabled={photoBusy} />
      </label>
      {photoMessage && <small role="status">{photoMessage}</small>}
    </div>
    <form className="manual-scan" onSubmit={submitManual}>
      <label htmlFor="manual-barcode">Enter barcode manually</label>
      <div><input id="manual-barcode" inputMode="numeric" autoComplete="off" value={manualBarcode} onChange={(event) => setManualBarcode(event.target.value)} placeholder="EAN, UPC, or Code 128" /><button className="button secondary">Look up</button></div>
    </form>
  </div>
}
