/**
 * Aujasya — Utility: cn() class name merger
 * Combines clsx + tailwind-merge for conflict-free class names.
 */

import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
