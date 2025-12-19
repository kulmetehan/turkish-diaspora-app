// Shared mascotte avatar component for onboarding screens
import TurkSpotBot from "@/assets/turkspotbot.png";
import { cn } from "@/lib/ui/cn";

export interface MascotteAvatarProps {
  size?: "sm" | "md" | "lg" | "xl";
  className?: string;
}

const sizeClasses = {
  sm: "h-16 w-16",
  md: "h-24 w-24",
  lg: "h-32 w-32",
  xl: "h-40 w-40",
};

export function MascotteAvatar({ size = "md", className }: MascotteAvatarProps) {
  return (
    <img
      src={TurkSpotBot}
      alt="TurkSpot Bot mascot"
      className={cn("object-contain", sizeClasses[size], className)}
    />
  );
}

