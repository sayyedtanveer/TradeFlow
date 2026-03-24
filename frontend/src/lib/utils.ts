import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

/**
 * Merges Tailwind classes dynamically.
 * Resolves conflicts natively (e.g., px-2 and px-4) to pure Tailwind output.
 * Essential for shadcn/ui.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
