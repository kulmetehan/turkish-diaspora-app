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

  // #region agent log
  fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'avatarUpload.ts:41',message:'getPublicUrl result',data:{urlData,publicUrl:urlData?.publicUrl,fileName},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
  // #endregion

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

