import * as React from "react";
import { cn } from "@/lib/ui/cn";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}
export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = "text", ...props }, ref) => (
    <input
      type={type}
      className={cn(
        "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm",
        "placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring ring-offset-2 ring-offset-background",
        className
      )}
      ref={ref}
      {...props}
    />
  )
);
Input.displayName = "Input";
