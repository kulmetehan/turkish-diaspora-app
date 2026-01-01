// Frontend/src/components/news/NewsIntroHeading.tsx
import { cn } from "@/lib/ui/cn";
import { useTranslation } from "@/hooks/useTranslation";

export interface NewsIntroHeadingProps {
  className?: string;
}

export function NewsIntroHeading({ className }: NewsIntroHeadingProps) {
  const { t } = useTranslation();
  return (
    <div className={cn("px-4 py-1.5", className)}>
      <h2 className="text-2xl font-gilroy font-black text-foreground">
        {t("news.heading")}
      </h2>
    </div>
  );
}








