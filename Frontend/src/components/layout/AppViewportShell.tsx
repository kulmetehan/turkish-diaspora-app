import React from "react";

import { cn } from "@/lib/ui/cn";

interface AppViewportShellProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  variant?: "map" | "content";
}

export function AppViewportShell({
  children,
  variant = "content",
  className,
  ...props
}: AppViewportShellProps) {
  const base = "relative h-[calc(100svh-var(--footer-height))] w-full transition-colors duration-200 motion-reduce:transition-none";
  const background = variant === "map" ? "bg-background" : "bg-surface-base";
  const mode =
    variant === "map"
      ? "overflow-hidden"
      : "overflow-auto";

  return (
    <div className={cn(base, background, mode, className)} {...props}>
      {children}
    </div>
  );
}

