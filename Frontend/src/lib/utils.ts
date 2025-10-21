// Frontend/src/lib/utils.ts
import { type ClassValue } from "clsx";
import clsx from "clsx";
import { twMerge } from "tailwind-merge";

// shadcn/ui helper: className merge
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
