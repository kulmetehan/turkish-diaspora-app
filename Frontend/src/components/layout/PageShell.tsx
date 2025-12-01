import React from "react";

import { cn } from "@/lib/ui/cn";

type PageShellMaxWidth = "4xl" | "5xl" | "full";

interface PageShellProps {
  children: React.ReactNode;
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  headerRight?: React.ReactNode;
  maxWidth?: PageShellMaxWidth;
  className?: string;
  headerClassName?: string;
}

const maxWidthClass: Record<PageShellMaxWidth, string> = {
  "4xl": "max-w-4xl",
  "5xl": "max-w-5xl",
  full: "max-w-[var(--layout-content-max)]",
};

export function PageShell({
  children,
  title,
  subtitle,
  headerRight,
  maxWidth = "5xl",
  className,
  headerClassName,
}: PageShellProps) {
  return (
    <div
      className={cn(
        "mx-auto flex w-full flex-col gap-6 px-4 py-10 text-foreground transition-colors duration-200 motion-reduce:transition-none",
        maxWidthClass[maxWidth],
        className,
      )}
    >
      {(title || subtitle || headerRight) && (
        <header
          className={cn(
            "flex flex-col gap-1 md:flex-row md:items-center md:justify-between",
            headerClassName,
          )}
        >
          <div className="space-y-1">
            {title && (
              <h1 className="text-xl font-semibold tracking-tight text-foreground md:text-2xl">
                {title}
              </h1>
            )}
            {subtitle && (
              <p className="text-sm text-muted-foreground md:text-base">
                {subtitle}
              </p>
            )}
          </div>
          {headerRight && (
            <div className="mt-3 md:mt-0">
              {headerRight}
            </div>
          )}
        </header>
      )}
      {children}
    </div>
  );
}

