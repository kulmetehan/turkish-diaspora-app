import { useEffect, useState } from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { cn } from "@/lib/ui/cn";
import { UserProfileHeader } from "./UserProfileHeader";
import { UserProfileStats } from "./UserProfileStats";
import { UserSocialLinks } from "./UserSocialLinks";
import { UserActivityFeed } from "./UserActivityFeed";
import { getUserProfileDetail, getUserActivity, type UserProfileDetail, type ActivityItem } from "@/lib/api";
import { toast } from "sonner";

interface UserProfileOverlayProps {
  userId: string;
  open: boolean;
  onClose: () => void;
  onUserClick?: (userId: string) => void;
}

export function UserProfileOverlay({ userId, open, onClose, onUserClick }: UserProfileOverlayProps) {
  const [profile, setProfile] = useState<UserProfileDetail | null>(null);
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    if (open && userId && userId.trim() !== "") {
      loadProfile();
    } else {
      setProfile(null);
      setActivities([]);
      setLoading(true);
    }
  }, [open, userId]);
  
  const loadProfile = async () => {
    setLoading(true);
    try {
      const [profileData, activityData] = await Promise.all([
        getUserProfileDetail(userId),
        getUserActivity(userId, { limit: 10 })
      ]);
      setProfile(profileData);
      setActivities(activityData);
    } catch (error: any) {
      console.error("Failed to load profile:", error);
      toast.error("Kon profiel niet laden");
      onClose();
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <DialogPrimitive.Root open={open} onOpenChange={(next) => { if (!next) onClose(); }}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay
          className={cn(
            "fixed inset-0 z-[70] bg-black/40 backdrop-blur",
            "pointer-events-none data-[state=open]:pointer-events-auto",
            "data-[state=closed]:animate-out data-[state=closed]:fade-out-0",
            "data-[state=open]:animate-in data-[state=open]:fade-in-0",
          )}
        />
        <DialogPrimitive.Content
          className={cn(
            "fixed inset-x-0 bottom-0 top-auto z-[75] mx-auto w-full max-w-screen-sm",
            "flex max-h-[min(90vh,800px)] flex-col rounded-t-[40px] border border-white/15 bg-surface-raised/95 text-foreground shadow-[0_-40px_80px_rgba(0,0,0,0.6)] backdrop-blur-2xl",
            "px-5 pt-6 pb-[calc(env(safe-area-inset-bottom)+20px)]",
            "focus:outline-none data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:slide-in-from-bottom",
            "data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:slide-out-to-bottom",
            "lg:left-1/2 lg:right-auto lg:top-1/2 lg:bottom-auto lg:max-h-[85vh] lg:w-[min(90vw,840px)] lg:max-w-[min(90vw,840px)] lg:-translate-x-1/2 lg:-translate-y-1/2",
            "lg:rounded-[40px] lg:px-6 lg:pb-6 lg:shadow-[0_45px_90px_rgba(0,0,0,0.6)]",
            "lg:data-[state=open]:zoom-in-95 lg:data-[state=closed]:zoom-out-95",
          )}
          aria-labelledby="profile-overlay-title"
        >
          <div className="flex items-center justify-between mb-4 pb-4 border-b border-white/10">
            <DialogPrimitive.Title
              id="profile-overlay-title"
              className="text-2xl font-semibold tracking-tight"
            >
              Profiel
            </DialogPrimitive.Title>
            <DialogPrimitive.Close className="rounded-sm opacity-70 transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-primary/30">
              <X className="h-5 w-5" aria-label="Sluiten" />
            </DialogPrimitive.Close>
          </div>

          <div className="flex-1 overflow-y-auto -mx-5 px-5">
            <div className="max-w-4xl mx-auto py-4">
              {loading ? (
                <div className="text-center py-8 text-muted-foreground">Laden...</div>
              ) : profile ? (
                <div className="flex flex-col gap-4">
                  <UserProfileHeader profile={profile} />
                  {profile.social_accounts.length > 0 && (
                    <UserSocialLinks accounts={profile.social_accounts} />
                  )}
                  <UserProfileStats stats={profile.stats} />
                  <UserActivityFeed 
                    userId={userId}
                    initialActivities={activities}
                    onUserClick={onUserClick}
                  />
                </div>
              ) : null}
            </div>
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

