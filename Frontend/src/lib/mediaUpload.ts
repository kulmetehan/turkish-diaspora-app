// Frontend/src/lib/mediaUpload.ts
import { supabase } from "@/lib/supabaseClient";

const MEDIA_BUCKET = "prikbord-media";
const MAX_FILE_SIZE_IMAGE = 5 * 1024 * 1024; // 5MB
const MAX_FILE_SIZE_VIDEO = 50 * 1024 * 1024; // 50MB
const ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp", "image/gif"];
const ALLOWED_VIDEO_TYPES = ["video/mp4", "video/webm", "video/quicktime"];

export interface MediaUploadResult {
  url: string;
  type: "image" | "video";
}

/**
 * Upload media file to Supabase Storage.
 * Returns the public URL of the uploaded media.
 */
export async function uploadMedia(file: File): Promise<MediaUploadResult> {
  const isImage = ALLOWED_IMAGE_TYPES.includes(file.type);
  const isVideo = ALLOWED_VIDEO_TYPES.includes(file.type);

  if (!isImage && !isVideo) {
    throw new Error("Alleen afbeeldingen (JPEG, PNG, WebP, GIF) en video's (MP4, WebM, MOV) zijn toegestaan");
  }

  // Validate file size
  const maxSize = isImage ? MAX_FILE_SIZE_IMAGE : MAX_FILE_SIZE_VIDEO;
  if (file.size > maxSize) {
    const maxSizeMB = maxSize / (1024 * 1024);
    throw new Error(`${isImage ? "Afbeelding" : "Video"} mag maximaal ${maxSizeMB}MB zijn`);
  }

  // Get current user ID from Supabase session
  const { data: { session } } = await supabase.auth.getSession();
  const userId = session?.user?.id || "anonymous";

  // Generate unique filename
  const timestamp = Date.now();
  const random = Math.random().toString(36).substring(2, 9);
  const extension = file.name.split(".").pop()?.toLowerCase() || (isImage ? "jpg" : "mp4");
  const fileName = `${userId}/${timestamp}-${random}.${extension}`;

  // Upload to Supabase Storage
  const { data, error } = await supabase.storage
    .from(MEDIA_BUCKET)
    .upload(fileName, file, {
      cacheControl: "3600",
      upsert: false,
    });

  if (error) {
    console.error("Media upload error:", error);
    throw new Error(`Upload mislukt: ${error.message}`);
  }

  // Get public URL
  const { data: urlData } = supabase.storage
    .from(MEDIA_BUCKET)
    .getPublicUrl(fileName);

  if (!urlData?.publicUrl) {
    throw new Error("Kon public URL niet ophalen");
  }

  return {
    url: urlData.publicUrl,
    type: isImage ? "image" : "video",
  };
}

/**
 * Create a preview URL from a File object.
 */
export function createMediaPreview(file: File): Promise<string> {
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

