// Frontend/src/lib/avatarUpload.ts
import { supabase } from "@/lib/supabaseClient";

const AVATAR_BUCKET = "avatars";
const MAX_FILE_SIZE = 2 * 1024 * 1024; // 2MB
const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"];

/**
 * Upload avatar to Supabase Storage.
 * Returns the public URL of the uploaded avatar.
 */
export async function uploadAvatar(file: File, userId: string): Promise<string> {
  // Validate file type
  if (!ALLOWED_TYPES.includes(file.type)) {
    throw new Error("Alleen JPEG, PNG en WebP afbeeldingen zijn toegestaan");
  }

  // Validate file size
  if (file.size > MAX_FILE_SIZE) {
    throw new Error("Afbeelding mag maximaal 2MB zijn");
  }

  // Get file extension
  const extension = file.name.split(".").pop()?.toLowerCase() || "jpg";
  const fileName = `${userId}.${extension}`;

  // Upload to Supabase Storage
  const { data, error } = await supabase.storage
    .from(AVATAR_BUCKET)
    .upload(fileName, file, {
      cacheControl: "3600",
      upsert: true, // Replace existing file
    });

  if (error) {
    console.error("Avatar upload error:", error);
    throw new Error(`Upload mislukt: ${error.message}`);
  }

  // Get public URL
  const { data: urlData } = supabase.storage
    .from(AVATAR_BUCKET)
    .getPublicUrl(fileName);

  if (!urlData?.publicUrl) {
    throw new Error("Kon public URL niet ophalen");
  }

  return urlData.publicUrl;
}

/**
 * Create a preview URL from a File object.
 */
export function createAvatarPreview(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      if (e.target?.result) {
        resolve(e.target.result as string);
      } else {
        reject(new Error("Kon preview niet maken"));
      }
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

