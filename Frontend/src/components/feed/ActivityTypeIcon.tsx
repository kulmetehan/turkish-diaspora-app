// Frontend/src/components/feed/ActivityTypeIcon.tsx
import { CheckCircle, Heart, MessageSquare, Vote, Star } from "lucide-react";
import { cn } from "@/lib/ui/cn";
import type { ActivityItem } from "@/lib/api";

interface ActivityTypeIconProps {
  activityType: ActivityItem["activity_type"];
  className?: string;
}

export function ActivityTypeIcon({ activityType, className }: ActivityTypeIconProps) {
  const iconProps = {
    className: cn("w-5 h-5", className),
  };

  switch (activityType) {
    case "check_in":
      return <CheckCircle {...iconProps} className={cn(iconProps.className, "text-blue-500")} />;
    case "reaction":
      return <Heart {...iconProps} className={cn(iconProps.className, "text-red-500")} />;
    case "note":
      return <MessageSquare {...iconProps} className={cn(iconProps.className, "text-green-500")} />;
    case "poll_response":
      return <Vote {...iconProps} className={cn(iconProps.className, "text-purple-500")} />;
    case "favorite":
      return <Star {...iconProps} className={cn(iconProps.className, "text-yellow-500")} />;
    default:
      return <CheckCircle {...iconProps} />;
  }
}


