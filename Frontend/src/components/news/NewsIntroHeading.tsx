// Frontend/src/components/news/NewsIntroHeading.tsx
import { cn } from "@/lib/ui/cn";

export interface NewsIntroHeadingProps {
  className?: string;
}

export function NewsIntroHeading({ className }: NewsIntroHeadingProps) {
  return (
    <div className={cn("px-4 py-1.5", className)}>
      <h2 className="text-2xl font-gilroy font-black text-foreground">
        Nieuws voor jou
      </h2>
    </div>
  );
}






