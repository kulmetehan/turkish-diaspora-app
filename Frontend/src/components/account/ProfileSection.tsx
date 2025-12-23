// Frontend/src/components/account/ProfileSection.tsx
import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/ui/cn";
import { toast } from "sonner";
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
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ProfileSection.tsx:44',message:'loadProfile START',data:{},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
      // #endregion
      const user = await getCurrentUser();
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ProfileSection.tsx:46',message:'getCurrentUser returned',data:{name:user?.name,avatar_url:user?.avatar_url,avatar_url_length:user?.avatar_url?.length},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
      // #endregion
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
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ProfileSection.tsx:62',message:'loadUsernameChangeStatus START',data:{},timestamp:Date.now(),sessionId:'debug-session',runId:'run4',hypothesisId:'L'})}).catch(()=>{});
      // #endregion
      const status = await getUsernameChangeStatus();
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ProfileSection.tsx:65',message:'getUsernameChangeStatus returned',data:{can_change:status.can_change,days_remaining:status.days_remaining,last_change:status.last_change,next_change_available:status.next_change_available},timestamp:Date.now(),sessionId:'debug-session',runId:'run4',hypothesisId:'M'})}).catch(()=>{});
      // #endregion
      setUsernameChangeStatus(status);
    } catch (error) {
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ProfileSection.tsx:68',message:'loadUsernameChangeStatus ERROR',data:{error:error instanceof Error ? error.message : String(error)},timestamp:Date.now(),sessionId:'debug-session',runId:'run4',hypothesisId:'N'})}).catch(()=>{});
      // #endregion
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
      toast.error("Alleen afbeeldingen zijn toegestaan");
      return;
    }

    if (file.size > 2 * 1024 * 1024) {
      toast.error("Afbeelding mag maximaal 2MB zijn");
      return;
    }

    setAvatarFile(file);
    try {
      const preview = await createAvatarPreview(file);
      setAvatarPreview(preview);
    } catch (error) {
      console.error("Failed to create preview:", error);
      toast.error("Kon preview niet maken");
    }
  };

  const handleSaveAvatar = async () => {
    if (!avatarFile || !userId) return;

    setIsUploadingAvatar(true);
    try {
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ProfileSection.tsx:115',message:'handleSaveAvatar START',data:{userId,fileName:avatarFile.name,fileSize:avatarFile.size},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
      // #endregion
      const avatarUrl = await uploadAvatar(avatarFile, userId);
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ProfileSection.tsx:120',message:'uploadAvatar returned URL',data:{avatarUrl,urlLength:avatarUrl?.length},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
      // #endregion
      await updateProfile({ avatar_url: avatarUrl });
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ProfileSection.tsx:122',message:'updateProfile completed',data:{avatarUrl},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
      // #endregion
      setProfile((prev) => prev ? { ...prev, avatar_url: avatarUrl } : null);
      setAvatarFile(null);
      setAvatarPreview(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      toast.success("Profielfoto bijgewerkt!");
    } catch (error) {
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ProfileSection.tsx:130',message:'handleSaveAvatar ERROR',data:{error:error instanceof Error ? error.message : String(error)},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
      // #endregion
      console.error("Failed to upload avatar:", error);
      toast.error(error instanceof Error ? error.message : "Upload mislukt");
    } finally {
      setIsUploadingAvatar(false);
    }
  };

  const handleSaveUsername = async () => {
    const trimmed = username.trim();
    
    if (trimmed.length < 2) {
      toast.error("Gebruikersnaam moet minimaal 2 karakters zijn");
      return;
    }

    if (trimmed.length > 50) {
      toast.error("Gebruikersnaam mag maximaal 50 karakters zijn");
      return;
    }

    if (usernameAvailable === false) {
      toast.error("Gebruikersnaam is al in gebruik");
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
      toast.success("Gebruikersnaam bijgewerkt!");
    } catch (error) {
      console.error("Failed to update username:", error);
      const errorMessage = error instanceof Error ? error.message : "Kon gebruikersnaam niet bijwerken";
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
        <p className="text-sm text-muted-foreground">Laden...</p>
      </div>
    );
  }

  return (
    <div className={cn("rounded-xl bg-surface-muted/50 p-6", className)}>
      <div className="space-y-6">
        <div className="space-y-1">
          <h2 className="text-lg font-gilroy font-medium text-foreground">
            Profiel
          </h2>
          <p className="text-sm text-muted-foreground">
            Beheer je gebruikersnaam en profielfoto
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
                    {avatarFile ? "Nieuwe foto geselecteerd" : "Wijzig profielfoto"}
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
                  {isUploadingAvatar ? "Uploaden..." : "Opslaan"}
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
                  Annuleren
                </Button>
              </div>
            )}
          </div>
        </div>

        {/* Username Section */}
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <label htmlFor="username" className="text-sm font-medium text-foreground">
              Gebruikersnaam:
            </label>
            <span className="text-sm text-foreground">
              {profile?.name || "Geen gebruikersnaam"}
            </span>
          </div>
          
          {isEditingUsername ? (
            <div className="space-y-2">
              <Input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="bijv. mehmet123"
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
                  <p className="text-xs text-muted-foreground">Controleren...</p>
                )}
                {!isCheckingUsername && username.trim().length >= 2 && usernameAvailable === true && (
                  <p className="text-xs text-green-600">✓ Beschikbaar</p>
                )}
                {!isCheckingUsername && username.trim().length >= 2 && usernameAvailable === false && (
                  <p className="text-xs text-destructive">✗ Al in gebruik</p>
                )}
                {!isCheckingUsername && username.trim().length > 0 && username.trim().length < 2 && (
                  <p className="text-xs text-muted-foreground">Minimaal 2 karakters</p>
                )}
              </div>
              <div className="flex gap-2">
                <Button
                  type="button"
                  size="sm"
                  onClick={handleSaveUsername}
                  disabled={!username.trim() || usernameAvailable === false || isSaving || isCheckingUsername || (usernameChangeStatus && !usernameChangeStatus.can_change)}
                >
                  {isSaving ? "Opslaan..." : "Opslaan"}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleCancelEdit}
                  disabled={isSaving}
                >
                  Annuleren
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
                  // #region agent log
                  fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ProfileSection.tsx:364',message:'Wijzigen button clicked',data:{usernameChangeStatus,can_change:usernameChangeStatus?.can_change,isDisabled:usernameChangeStatus && !usernameChangeStatus.can_change},timestamp:Date.now(),sessionId:'debug-session',runId:'run4',hypothesisId:'O'})}).catch(()=>{});
                  // #endregion
                  setIsEditingUsername(true);
                }}
                disabled={usernameChangeStatus && !usernameChangeStatus.can_change}
                className="p-0 h-auto text-sm text-primary hover:text-primary/80 hover:underline"
              >
                Wijzigen
              </Button>
              {usernameChangeStatus && !usernameChangeStatus.can_change && (
                <p className="text-xs text-muted-foreground">
                  Volgende wijziging mogelijk over {usernameChangeStatus.days_remaining} dag{usernameChangeStatus.days_remaining !== 1 ? "en" : ""}
                </p>
              )}
              {/* #region agent log */}
              {(() => {
                fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ProfileSection.tsx:370',message:'Wijzigen button render',data:{usernameChangeStatus_exists:!!usernameChangeStatus,can_change:usernameChangeStatus?.can_change,isDisabled:usernameChangeStatus && !usernameChangeStatus.can_change,profile_name:profile?.name},timestamp:Date.now(),sessionId:'debug-session',runId:'run4',hypothesisId:'P'})}).catch(()=>{});
                return null;
              })()}
              {/* #endregion */}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

