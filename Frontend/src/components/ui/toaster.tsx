import * as React from "react";

import { Toaster as SonnerToaster } from "sonner";

import { cn } from "@/lib/utils";

/**
 * Public Toaster wrapper:
 * - Accepts all Sonner Toaster props (position, toastOptions, richColors, etc.).
 * - Adds a default top offset class for safe-area alignment.
 * - Merges any caller-provided className.
 */
export type ToasterProps = React.ComponentProps<typeof SonnerToaster>;

export function Toaster({ className, ...props }: ToasterProps) {
  return (
    <SonnerToaster
      className={cn("mt-[var(--top-offset)]", className)}
      {...props}
    />
  );
}

export default Toaster;
