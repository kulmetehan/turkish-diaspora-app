import { cn } from "@/lib/ui/cn";
import mekaninsahibiIcon from "@/assets/mekaninsahibi.png";
import { MascotteAvatar } from "@/components/onboarding/MascotteAvatar";

interface RoleAvatarProps {
  role: string | null | undefined;
  licensePlate: string | null | undefined;
  className?: string;
  size?: "sm" | "md" | "lg";
}

/**
 * Get role avatar image based on role.
 * For "Yeni Gelen" and "Mekanın sahibi", the avatar should match the origin city.
 * Uses existing assets (mekaninsahibi.png for location_owner, MascotteAvatar for yeni_gelen).
 */
export function RoleAvatar({ role, licensePlate, className, size = "sm" }: RoleAvatarProps) {
  if (!role) {
    return null;
  }

  // For location_owner (Mekanın sahibi), use the icon
  if (role === "location_owner") {
    return (
      <img
        src={mekaninsahibiIcon}
        alt="Mekanın sahibi"
        className={cn(
          "object-contain",
          size === "sm" && "h-4 w-4",
          size === "md" && "h-6 w-6",
          size === "lg" && "h-8 w-8",
          className
        )}
      />
    );
  }

  // For yeni_gelen (Yeni Gelen), use MascotteAvatar
  if (role === "yeni_gelen") {
    return (
      <div className={cn(className)}>
        <MascotteAvatar size={size} />
      </div>
    );
  }

  return null;
}




