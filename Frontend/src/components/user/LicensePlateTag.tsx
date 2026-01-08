import { cn } from "@/lib/ui/cn";

interface LicensePlateTagProps {
  licensePlate: string | null | undefined;
  className?: string;
}

export function LicensePlateTag({ licensePlate, className }: LicensePlateTagProps) {
  if (!licensePlate) {
    return null;
  }

  return (
    <span
      className={cn(
        "inline-flex items-center justify-center",
        "px-1.5 py-0.5 rounded-md",
        "text-xs font-gilroy font-semibold",
        "bg-primary/10 text-primary",
        "border border-primary/20",
        className
      )}
      title={`Kenteken: ${licensePlate}`}
    >
      {licensePlate}
    </span>
  );
}



