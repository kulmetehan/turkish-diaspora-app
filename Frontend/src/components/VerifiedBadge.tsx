// Frontend/src/components/VerifiedBadge.tsx
import { Icon } from "@/components/Icon";
import { cn } from "@/lib/ui/cn";
import { useTranslation } from "@/hooks/useTranslation";

interface VerifiedBadgeProps {
  className?: string;
  size?: "sm" | "md" | "lg";
}

const sizeMap = {
  sm: 0.875,
  md: 1,
  lg: 1.25,
};

export function VerifiedBadge({ className, size = "md" }: VerifiedBadgeProps) {
  const { t } = useTranslation();
  const iconSize = sizeMap[size];
  
  return (
    <Icon
      name="BadgeCheck"
      sizeRem={iconSize}
      className={cn(
        "text-blue-500 flex-shrink-0",
        className
      )}
      aria-label={t("location.verifiedByOwner")}
      title={t("location.verifiedByOwner")}
      decorative={false}
    />
  );
}

