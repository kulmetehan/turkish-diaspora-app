// Onboarding Screen 6: Username & Avatar Setup
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { MascotteAvatar } from "./MascotteAvatar";
import { cn } from "@/lib/ui/cn";
import { useState, useRef, useEffect } from "react";
import { toast } from "sonner";
import { checkUsernameAvailable, updateProfile } from "@/lib/api";
import { uploadAvatar, createAvatarPreview } from "@/lib/avatarUpload";
import { useUserAuth } from "@/hooks/useUserAuth";
import { trackOnboardingDataCollected } from "@/lib/analytics";
import { X, User } from "lucide-react";

export interface OnboardingScreen6Props {
  onComplete: () => void;
}

export function OnboardingScreen6({ onComplete }: OnboardingScreen6Props) {
  const { userId } = useUserAuth();
  const [username, setUsername] = useState("");
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
  const [isCheckingUsername, setIsCheckingUsername] = useState(false);
  const [usernameAvailable, setUsernameAvailable] = useState<boolean | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Debounced username availability check
  useEffect(() => {
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
    }, 500); // 500ms debounce

    return () => clearTimeout(timeoutId);
  }, [username]);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith("image/")) {
      toast.error("Alleen afbeeldingen zijn toegestaan");
      return;
    }

    // Validate file size (2MB)
    if (file.size > 2 * 1024 * 1024) {
      toast.error("Afbeelding mag maximaal 2MB zijn");
      return;
    }

    setAvatarFile(file);

    // Track avatar upload
    trackOnboardingDataCollected(6, "username_avatar", "avatar", file.name);

    // Create preview
    try {
      const preview = await createAvatarPreview(file);
      setAvatarPreview(preview);
    } catch (error) {
      console.error("Failed to create preview:", error);
      toast.error("Kon preview niet maken");
    }
  };

  const handleRemoveAvatar = () => {
    setAvatarFile(null);
    setAvatarPreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleSubmit = async () => {
    const trimmedUsername = username.trim();

    // Validate username
    if (trimmedUsername.length < 2) {
      toast.error("Gebruikersnaam moet minimaal 2 karakters zijn");
      return;
    }

    if (trimmedUsername.length > 50) {
      toast.error("Gebruikersnaam mag maximaal 50 karakters zijn");
      return;
    }

    if (usernameAvailable === false) {
      toast.error("Gebruikersnaam is al in gebruik");
      return;
    }

    if (isCheckingUsername) {
      toast.error("Wacht even, gebruikersnaam wordt gecontroleerd...");
      return;
    }

    setIsSubmitting(true);

    try {
      let avatarUrl: string | null = null;

      // Upload avatar if selected
      if (avatarFile && userId) {
        setIsUploading(true);
        try {
          avatarUrl = await uploadAvatar(avatarFile, userId);
        } catch (error) {
          console.error("Avatar upload failed:", error);
          toast.error(error instanceof Error ? error.message : "Avatar upload mislukt");
          setIsUploading(false);
          setIsSubmitting(false);
          return;
        } finally {
          setIsUploading(false);
        }
      }

      // Track username collection
      trackOnboardingDataCollected(6, "username_avatar", "username", trimmedUsername);

      // Update profile with username and avatar
      await updateProfile({
        display_name: trimmedUsername,
        avatar_url: avatarUrl,
      });

      toast.success("Profiel bijgewerkt!");
      onComplete();
    } catch (error) {
      console.error("Failed to update profile:", error);
      toast.error(
        error instanceof Error
          ? error.message
          : "Kon profiel niet bijwerken. Probeer het opnieuw."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const isUsernameValid = username.trim().length >= 2 && username.trim().length <= 50;
  const canSubmit = isUsernameValid && usernameAvailable !== false && !isCheckingUsername && !isSubmitting && !isUploading;

  return (
    <div className="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-background px-6 overflow-y-auto py-8">
      {/* Mascotte */}
      <div className="mb-6">
        <MascotteAvatar size="lg" />
      </div>

      {/* Title */}
      <h1 className="text-2xl font-gilroy font-bold text-foreground mb-2 text-center">
        Kies je gebruikersnaam
      </h1>
      <p className="text-sm text-muted-foreground mb-6 text-center max-w-md">
        Kies een unieke gebruikersnaam en upload een profielfoto (optioneel)
      </p>

      <div className="w-full max-w-md space-y-6">
        {/* Avatar Upload */}
        <div className="flex flex-col items-center space-y-4">
          <div className="relative">
            {avatarPreview ? (
              <div className="relative">
                <img
                  src={avatarPreview}
                  alt="Avatar preview"
                  className="w-24 h-24 rounded-full object-cover border-2 border-primary"
                />
                <button
                  type="button"
                  onClick={handleRemoveAvatar}
                  className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-destructive text-destructive-foreground flex items-center justify-center hover:bg-destructive/90 transition-colors"
                  aria-label="Verwijder avatar"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            ) : (
              <div className="w-24 h-24 rounded-full bg-muted border-2 border-dashed border-muted-foreground/30 flex items-center justify-center">
                <User className="h-8 w-8 text-muted-foreground" />
              </div>
            )}
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleFileSelect}
            className="hidden"
            id="avatar-upload"
          />
          <label htmlFor="avatar-upload">
            <Button
              type="button"
              variant="outline"
              size="sm"
              asChild
              disabled={isUploading}
            >
              <span>
                {avatarFile ? "Wijzig foto" : "Upload foto"}
              </span>
            </Button>
          </label>
          {isUploading && (
            <p className="text-xs text-muted-foreground">Uploaden...</p>
          )}
        </div>

        {/* Username Input */}
        <div className="space-y-2">
          <label htmlFor="username" className="text-sm font-medium text-foreground">
            Gebruikersnaam *
          </label>
          <Input
            id="username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="bijv. mehmet123"
            minLength={2}
            maxLength={50}
            disabled={isSubmitting || isUploading}
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
        </div>

        {/* Submit Button */}
        <Button
          onClick={handleSubmit}
          size="lg"
          variant="default"
          className="w-full font-gilroy"
          disabled={!canSubmit}
          aria-label="Voltooien"
        >
          {isSubmitting ? "Bezig..." : "Voltooien"}
        </Button>
      </div>
    </div>
  );
}

