import * as React from "react";

import { cn } from "@/lib/ui/cn";

export interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
    value?: number;
}

const Progress = React.forwardRef<HTMLDivElement, ProgressProps>(
    ({ className, value = 0, ...props }, ref) => {
        const clamped = Math.min(100, Math.max(0, value ?? 0));
        return (
            <div
                ref={ref}
                className={cn(
                    "h-2 w-full overflow-hidden rounded-full bg-muted",
                    className
                )}
                role="progressbar"
                aria-valuenow={clamped}
                aria-valuemin={0}
                aria-valuemax={100}
                {...props}
            >
                <div
                    className="h-full rounded-full bg-primary transition-[width]"
                    style={{ width: `${clamped}%` }}
                />
            </div>
        );
    }
);
Progress.displayName = "Progress";

export { Progress };
