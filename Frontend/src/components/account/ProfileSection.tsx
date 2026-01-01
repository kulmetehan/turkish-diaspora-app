// Frontend/src/components/account/ProfileSection.tsx
import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/ui/cn";
import { toast } from "sonner";
import { useTranslation } from "@/hooks/useTranslation";
import { 
  getCurrentUser, 
  checkUsernameAvailable, 
  updateProfile,
  getUsernameChangeStatus,
  type UsernameChangeStatus
} from "@/lib/api";
import { uploadAvatar, createAvatarPreview } from "@/lib/avatarUpload";
import { useUserAuth } from "@/hooks/useUserAuth";
import { X, User, Camera } from "lucide-react";

interface ProfileSectionProps {
  className?: string;
}

export function ProfileSection({ className }: ProfileSectionProps) {
  const { t } = useTranslation();
  const { userId } = useUserAuth();
  const [profile, setProfile] = useState<{ name: string | null; avatar_url: string | null } | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isEditingUsername, setIsEditingUsername] = useState(false);
  const [username, setUsername] = useState("");
  const [isCheckingUsername, setIsCheckingUsername] = useState(false);
  const [usernameAvailable, setUsernameAvailable] = useState<boolean | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [usernameChangeStatus, setUsernameChangeStatus] = useState<UsernameChangeStatus | null>(null);
  
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
  const [isUploadingAvatar, setIsUploadingAvatar] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load profile and username change status on mount
  useEffect(() => {
    loadProfile();
    loadUsernameChangeStatus();
  }, []);

  const loadProfile = async () => {
    try {
      const user = await getCurrentUser();
      setProfile(user);
      setUsername(user?.name || "");
    } catch (error) {
      console.error("Failed to load profile:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadUsernameChangeStatus = async () => {
    try {
      const status = await getUsernameChangeStatus();
      setUsernameChangeStatus(status);
    } catch (error) {
      console.error("Failed to load username change status:", error);
    }
  };

  // Debounced username check
  useEffect(() => {
    if (!isEditingUsername) return;
    
    const trimmed = username.trim();
    if (trimmed.length < 2) {
      setUsernameAvailable(null);
      return;
    }

    const timeoutId = setTimeout(async () => {
      setIsCheckingUsername(true);
      try {
        const result = await checkUsernameAvailable(trimmed);
        setUsernameAvailable(result.available);
      } catch (error) {
        console.error("Failed to check username:", error);
        setUsernameAvailable(null);
      } finally {
        setIsCheckingUsername(false);
      }
    }, 500);

    return () => clearTimeout(timeoutId);
  }, [username, isEditingUsername]);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      toast.error(t("toast.upload.imageOnly"));
      return;
    }

    if (file.size > 2 * 1024 * 1024) {
      toast.error(t("toast.upload.maxSize"));
      return;
    }

    setAvatarFile(file);
    try {
      const preview = await createAvatarPreview(file);
      setAvatarPreview(preview);
    } catch (error) {
      console.error("Failed to create preview:", error);
      toast.error(t("toast.upload.previewFailed"));
    }
  };

  const handleSaveAvatar = async () => {
    if (!avatarFile || !userId) return;

    setIsUploadingAvatar(true);
    try {
      const avatarUrl = await uploadAvatar(avatarFile, userId);
      await updateProfile({ avatar_url: avatarUrl });
      setProfile((prev) => prev ? { ...prev, avatar_url: avatarUrl } : null);
      setAvatarFile(null);
      setAvatarPreview(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      toast.success(t("toast.profile.avatarUpdated"));
    } catch (error) {
      console.error("Failed to upload avatar:", error);
      toast.error(error instanceof Error ? error.message : t("toast.upload.error"));
    } finally {
      setIsUploadingAvatar(false);
    }
  };

  const handleSaveUsername = async () => {
    const trimmed = username.trim();
    
    if (trimmed.length < 2) {
      toast.error(t("toast.username.minLength"));
      return;
    }

    if (trimmed.length > 50) {
      toast.error(t("toast.username.maxLength"));
      return;
    }

    if (usernameAvailable === false) {
      toast.error(t("toast.username.taken"));
      return;
    }

    if (trimmed === profile?.name) {
      setIsEditingUsername(false);
      return;
    }

    setIsSaving(true);
    try {
      await updateProfile({ display_name: trimmed });
      setProfile((prev) => prev ? { ...prev, name: trimmed } : null);
      setIsEditingUsername(false);
      // Reload username change status after successful change
      await loadUsernameChangeStatus();
      toast.success(t("toast.profile.usernameUpdated"));
    } catch (error) {
      console.error("Failed to update username:", error);
      const errorMessage = error instanceof Error ? error.message : t("toast.profile.usernameUpdateFailed");
      toast.error(errorMessage);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancelEdit = () => {
    setUsername(profile?.name || "");
    setIsEditingUsername(false);
    setUsernameAvailable(null);
  };

  if (isLoading) {
    return (
      <div className={cn("rounded-xl bg-surface-muted/50 p-6", className)}>
        <p className="text-sm text-muted-foreground">{t("common.loading")}</p>
      </div>
    );
  }

  return (
    <div className={cn("rounded-xl bg-surface-muted/50 p-6", className)}>
      <div className="space-y-6">
        <div className="space-y-1">
          <h2 className="text-lg font-gilroy font-medium text-foreground">
            {t("account.profile.title")}
          </h2>
          <p className="text-sm text-muted-foreground">
            {t("account.profile.description")}
          </p>
        </div>

        {/* Avatar Section */}
        <div className="flex items-start gap-4">
          <div className="relative">
            {avatarPreview || profile?.avatar_url ? (
              <img
                src={avatarPreview || profile?.avatar_url || ""}
                alt="Avatar"
                className="w-20 h-20 rounded-full object-cover border-2 border-primary"
              />
            ) : (
              <div className="w-20 h-20 rounded-full bg-muted border-2 border-dashed border-muted-foreground/30 flex items-center justify-center">
                <User className="h-10 w-10 text-muted-foreground" />
              </div>
            )}
          </div>
          
          <div className="flex-1 space-y-2">
            <div>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleFileSelect}
                className="hidden"
                id="avatar-upload-profile"
              />
              <label htmlFor="avatar-upload-profile">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  asChild
                  disabled={isUploadingAvatar}
                >
                  <span className="flex items-center gap-2">
                    <Camera className="h-4 w-4" />
                    {avatarFile ? t("account.profile.newPhotoSelected") : t("account.profile.changePhoto")}
                  </span>
                </Button>
              </label>
            </div>
            
            {avatarFile && (
              <div className="flex gap-2">
                <Button
                  type="button"
                  size="sm"
                  onClick={handleSaveAvatar}
                  disabled={isUploadingAvatar}
                >
                  {isUploadingAvatar ? t("account.profile.uploading") : t("account.profile.save")}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setAvatarFile(null);
                    setAvatarPreview(null);
                    if (fileInputRef.current) {
                      fileInputRef.current.value = "";
                    }
                  }}
                >
                  {t("account.profile.cancel")}
                </Button>
              </div>
            )}
          </div>
        </div>

        {/* Username Section */}
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <label htmlFor="username" className="text-sm font-medium text-foreground">
              {t("account.profile.username")}
            </label>
            <span className="text-sm text-foreground">
              {profile?.name || t("account.profile.noUsername")}
            </span>
          </div>
          
          {isEditingUsername ? (
            <div className="space-y-2">
              <Input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder={t("onboarding.username.placeholder")}
                minLength={2}
                maxLength={50}
                disabled={isSaving || isCheckingUsername || (usernameChangeStatus && !usernameChangeStatus.can_change)}
                className={cn(
                  usernameAvailable === false && "border-destructive",
                  usernameAvailable === true && "border-green-500"
                )}
              />
              <div className="h-5">
                {isCheckingUsername && (
                  <p className="text-xs text-muted-foreground">{t("onboarding.username.checking")}</p>
                )}
                {!isCheckingUsername && username.trim().length >= 2 && usernameAvailable === true && (
                  <p className="text-xs text-green-600">{t("onboarding.username.available")}</p>
                )}
                {!isCheckingUsername && username.trim().length >= 2 && usernameAvailable === false && (
                  <p className="text-xs text-destructive">{t("onboarding.username.taken")}</p>
                )}
                {!isCheckingUsername && username.trim().length > 0 && username.trim().length < 2 && (
                  <p className="text-xs text-muted-foreground">{t("onboarding.username.minChars")}</p>
                )}
              </div>
              <div className="flex gap-2">
                <Button
                  type="button"
                  size="sm"
                  onClick={handleSaveUsername}
                  disabled={!username.trim() || usernameAvailable === false || isSaving || isCheckingUsername || (usernameChangeStatus && !usernameChangeStatus.can_change)}
                >
                  {isSaving ? t("account.profile.saving") : t("account.profile.save")}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleCancelEdit}
                  disabled={isSaving}
                >
                  {t("account.profile.cancel")}
                </Button>
              </div>
            </div>
          ) : (
            <>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => {
                  setIsEditingUsername(true);
                }}
                disabled={usernameChangeStatus && !usernameChangeStatus.can_change}
                className="p-0 h-auto text-sm text-primary hover:text-primary/80 hover:underline"
              >
                {t("account.profile.edit")}
              </Button>
              {usernameChangeStatus && !usernameChangeStatus.can_change && (
                <p className="text-xs text-muted-foreground">
                  {usernameChangeStatus.days_remaining === 1 
                    ? t("account.profile.daysRemaining").replace("{count}", "1")
                    : t("account.profile.daysRemainingPlural").replace("{count}", usernameChangeStatus.days_remaining.toString())}
                </p>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

