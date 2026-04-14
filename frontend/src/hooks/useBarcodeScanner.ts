import { useCallback, useEffect, useRef, useState } from 'react'
import { BrowserMultiFormatReader } from '@zxing/library'

export interface BarcodeResult {
  value: string
  format: string
  timestamp: number
}

export interface BarcodeScannerOptions {
  onScan?: (result: BarcodeResult) => void
  onError?: (error: Error) => void
  facingMode?: 'user' | 'environment'
  autoStart?: boolean
}

/**
 * Hook for barcode scanning with native BarcodeDetector API
 * and fallback to @zxing/library
 */
export const useBarcodeScanner = (options: BarcodeScannerOptions = {}) => {
  const {
    onScan,
    onError,
    facingMode = 'environment',
    autoStart = false,
  } = options

  const [isScanning, setIsScanning] = useState(false)
  const [hasPermission, setHasPermission] = useState<boolean | null>(null)
  const [usesBarcodeDetectorAPI, setUsesBarcodeDetectorAPI] = useState(false)

  const videoRef = useRef<HTMLVideoElement | null>(null)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const readerRef = useRef<BrowserMultiFormatReader | null>(null)
  const animationFrameRef = useRef<number>()

  // Request camera permission
  const requestPermission = useCallback(async (): Promise<boolean> => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode },
      })
      streamRef.current = stream
      setHasPermission(true)
      return true
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Camera access denied')
      setHasPermission(false)
      onError?.(error)
      return false
    }
  }, [facingMode, onError])

  // Check for native BarcodeDetector API support
  const checkBarcodeDetectorSupport = useCallback((): boolean => {
    return 'BarcodeDetector' in window
  }, [])

  // Scan using native BarcodeDetector API
  const scanWithBarcodeDetector = useCallback(async () => {
    if (!videoRef.current || !canvasRef.current) return

    try {
      const detector = new (window as any).BarcodeDetector({
        formats: ['ean_13', 'ean_8', 'code_128', 'qr_code'],
      })

      const scanFrame = async () => {
        if (!videoRef.current || !canvasRef.current || !isScanning) return

        try {
          const canvasContext = canvasRef.current.getContext('2d')
          if (canvasContext && videoRef.current.readyState === videoRef.current.HAVE_ENOUGH_DATA) {
            canvasContext.drawImage(videoRef.current, 0, 0, canvasRef.current.width, canvasRef.current.height)

            const barcodes = await detector.detect(canvasRef.current)

            if (barcodes.length > 0) {
              const barcode = barcodes[0]
              const result: BarcodeResult = {
                value: barcode.rawValue,
                format: barcode.format,
                timestamp: Date.now(),
              }
              onScan?.(result)
            }
          }
        } catch (err) {
          // Continue scanning on error
        }

        animationFrameRef.current = requestAnimationFrame(scanFrame)
      }

      scanFrame()
    } catch (err) {
      const error = err instanceof Error ? err : new Error('BarcodeDetector error')
      onError?.(error)
    }
  }, [isScanning, onScan, onError])

  // Scan using ZXing library (fallback)
  const scanWithZXing = useCallback(async () => {
    if (!videoRef.current) return

    if (!readerRef.current) {
      readerRef.current = new BrowserMultiFormatReader()
    }

    try {
      const reader = readerRef.current

      const scanFrame = async () => {
        if (!videoRef.current || !isScanning) return

        try {
          const result = await reader.decodeFromVideoElement(videoRef.current)
          if (result) {
            const barcode: BarcodeResult = {
              value: result.getText(),
              format: result.getBarcodeFormat().toString(),
              timestamp: Date.now(),
            }
            onScan?.(barcode)
          }
        } catch (err) {
          // Continue scanning on error
        }

        animationFrameRef.current = requestAnimationFrame(scanFrame)
      }

      scanFrame()
    } catch (err) {
      const error = err instanceof Error ? err : new Error('ZXing error')
      onError?.(error)
    }
  }, [isScanning, onScan, onError])

  // Start scanning
  const startScanning = useCallback(async (): Promise<boolean> => {
    if (isScanning) return true
    if (hasPermission === false) {
      const granted = await requestPermission()
      if (!granted) return false
    }

    if (!videoRef.current || !streamRef.current) {
      const granted = await requestPermission()
      if (!granted) return false
    }

    // Attach stream to video element
    if (videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current
      await videoRef.current.play()
    }

    setIsScanning(true)

    // Use native BarcodeDetector if available, otherwise fallback to ZXing
    if (checkBarcodeDetectorSupport()) {
      setUsesBarcodeDetectorAPI(true)
      scanWithBarcodeDetector()
    } else {
      setUsesBarcodeDetectorAPI(false)
      scanWithZXing()
    }

    return true
  }, [isScanning, hasPermission, requestPermission, checkBarcodeDetectorSupport, scanWithBarcodeDetector, scanWithZXing])

  // Stop scanning
  const stopScanning = useCallback(() => {
    if (!isScanning) return

    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current)
    }

    if (videoRef.current) {
      videoRef.current.pause()
      videoRef.current.srcObject = null
    }

    setIsScanning(false)
  }, [isScanning])

  // Cleanup
  useEffect(() => {
    return () => {
      stopScanning()
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop())
      }
    }
  }, [stopScanning])

  // Auto-start if requested
  useEffect(() => {
    if (autoStart && !isScanning && hasPermission === null) {
      requestPermission().then((granted) => {
        if (granted) {
          startScanning()
        }
      })
    }
  }, [autoStart, isScanning, hasPermission, requestPermission, startScanning])

  return {
    // State
    isScanning,
    hasPermission,
    usesBarcodeDetectorAPI,

    // Controls
    startScanning,
    stopScanning,
    requestPermission,

    // Refs
    videoRef,
    canvasRef,
  }
}

export default useBarcodeScanner
