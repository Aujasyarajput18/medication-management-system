/**
 * Aujasya — Image Preprocessing for OCR
 * Canvas API preprocessing: greyscale, contrast, adaptive threshold.
 * Runs on main thread (fast enough for single images).
 */

export interface PreprocessOptions {
  greyscale?: boolean;
  contrast?: number; // 1.0 = normal, 1.5 = high
  maxWidth?: number;
  maxHeight?: number;
}

const DEFAULT_OPTIONS: PreprocessOptions = {
  greyscale: true,
  contrast: 1.4,
  maxWidth: 2048,
  maxHeight: 2048,
};

/**
 * Preprocess an image for OCR: resize, greyscale, contrast enhance.
 * Returns a Blob suitable for Tesseract or server upload.
 */
export async function preprocessImage(
  file: File | Blob,
  options: PreprocessOptions = {}
): Promise<Blob> {
  const opts = { ...DEFAULT_OPTIONS, ...options };
  const bitmap = await createImageBitmap(file);
  
  // Calculate dimensions maintaining aspect ratio
  let { width, height } = bitmap;
  const maxW = opts.maxWidth!;
  const maxH = opts.maxHeight!;
  
  if (width > maxW || height > maxH) {
    const scale = Math.min(maxW / width, maxH / height);
    width = Math.round(width * scale);
    height = Math.round(height * scale);
  }

  const canvas = new OffscreenCanvas(width, height);
  const ctx = canvas.getContext('2d')!;
  
  // Draw resized image
  ctx.drawImage(bitmap, 0, 0, width, height);
  bitmap.close();

  // Get pixel data for processing
  const imageData = ctx.getImageData(0, 0, width, height);
  const data = imageData.data;

  for (let i = 0; i < data.length; i += 4) {
    let r = data[i], g = data[i + 1], b = data[i + 2];

    // Greyscale conversion (luminance-weighted)
    if (opts.greyscale) {
      const grey = Math.round(0.299 * r + 0.587 * g + 0.114 * b);
      r = g = b = grey;
    }

    // Contrast adjustment
    if (opts.contrast && opts.contrast !== 1.0) {
      const factor = (259 * (opts.contrast * 128 + 255)) / (255 * (259 - opts.contrast * 128));
      r = Math.min(255, Math.max(0, Math.round(factor * (r - 128) + 128)));
      g = Math.min(255, Math.max(0, Math.round(factor * (g - 128) + 128)));
      b = Math.min(255, Math.max(0, Math.round(factor * (b - 128) + 128)));
    }

    data[i] = r;
    data[i + 1] = g;
    data[i + 2] = b;
  }

  ctx.putImageData(imageData, 0, 0);
  return canvas.convertToBlob({ type: 'image/jpeg', quality: 0.92 });
}

/**
 * Convert a File/Blob to base64 data URL for preview.
 */
export function fileToDataUrl(file: File | Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}
