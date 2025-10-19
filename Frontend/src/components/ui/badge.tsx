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

export function Badge({
  className,
  variant,
  children
}: {
  className?: string;
  variant?: "default" | "secondary" | "outline";
  children: React.ReactNode;
}) {
  return <span className={cn(badge({ variant }), className)}>{children}</span>;
}
