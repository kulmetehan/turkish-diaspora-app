import * as React from "react";
import { cva } from "class-variance-authority";
import { cn } from "@/lib/ui/cn";

const badge = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground",
        secondary: "border-transparent bg-secondary text-secondary-foreground",
        outline: "text-foreground",
      }
    },
    defaultVariants: { variant: "default" }
  }
);

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "secondary" | "outline";
  children: React.ReactNode;
}

export function Badge({
  className,
  variant,
  children,
  ...props
}: BadgeProps) {
  return <span className={cn(badge({ variant }), className)} {...props}>{children}</span>;
}
