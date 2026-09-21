import { clsx, type ClassValue } from "clsx";

/** Compose conditional class names. Variants belong in lookup maps, not if/else chains. */
export function cn(...inputs: ClassValue[]): string {
  return clsx(inputs);
}
