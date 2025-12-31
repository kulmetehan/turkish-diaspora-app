// Frontend/src/lib/avatarUpload.ts
import { supabase } from "@/lib/supabaseClient";

const AVATAR_BUCKET = "avatars";
const MAX_FILE_SIZE = 2 * 1024 * 1024; // 2MB
const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"];
const AVATAR_SIZE = 400; // 400x400px for sharp display
const MIN_IMAGE_SIZE = 200; // Minimum 200x200px

/**
 * Validate image dimensions (minimum size check).
 */
function validateImageDimensions(file: File): Promise<boolean> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const reader = new FileReader();

    reader.onload = (e) => {
      img.onload = () => {
        // Check minimum size (at least 200x200)
        if (img.width < MIN_IMAGE_SIZE || img.height < MIN_IMAGE_SIZE) {
          reject(
            new Error(
              `Afbeelding moet minimaal ${MIN_IMAGE_SIZE}x${MIN_IMAGE_SIZE} pixels zijn. ` +
                `Huidige afmetingen: ${img.width}x${img.height}px`
            )
          );
          return;
        }
        resolve(true);
      };
      img.onerror = () => reject(new Error("Kon afbeelding niet laden"));
      img.src = e.target?.result as string;
    };

    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

/**
 * Crop image to square and resize to target size.
 */
function cropImageToSquare(file: File): Promise<File> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const reader = new FileReader();

    reader.onload = (e) => {
      img.onload = () => {
        // Calculate square crop (center crop)
        const size = Math.min(img.width, img.height);
        const x = (img.width - size) / 2;
        const y = (img.height - size) / 2;

        // Create canvas
        const canvas = document.createElement("canvas");
        canvas.width = AVATAR_SIZE;
        canvas.height = AVATAR_SIZE;
        const ctx = canvas.getContext("2d");

        if (!ctx) {
          reject(new Error("Kon canvas context niet maken"));
          return;
        }

        // Draw cropped and resized image
        ctx.drawImage(
          img,
          x, y, size, size, // Source crop
          0, 0, AVATAR_SIZE, AVATAR_SIZE // Destination size
        );

        // Convert to blob
        canvas.toBlob(
          (blob) => {
            if (!blob) {
              reject(new Error("Kon afbeelding niet converteren"));
              return;
            }
            // Create new File with same name but .png extension
            const croppedFile = new File(
              [blob],
              file.name.replace(/\.[^/.]+$/, ".png"),
              { type: "image/png" }
            );
            resolve(croppedFile);
          },
          "image/png",
          0.95 // Quality
        );
      };

      img.onerror = () => reject(new Error("Kon afbeelding niet laden"));
      img.src = e.target?.result as string;
    };

    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

/**
 * Upload avatar to Supabase Storage.
 * Automatically crops to square and resizes.
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

  // Validate dimensions
  try {
    await validateImageDimensions(file);
  } catch (error) {
    throw error; // Re-throw validation error
  }

  // Crop to square and resize
  let processedFile: File;
  try {
    processedFile = await cropImageToSquare(file);
  } catch (error) {
    console.error("Crop error:", error);
    throw new Error("Kon afbeelding niet verwerken. Probeer een andere foto.");
  }

  // Validate processed file size
  if (processedFile.size > MAX_FILE_SIZE) {
    throw new Error("Verwerkte afbeelding is te groot. Probeer een kleinere foto.");
  }

  const fileName = `${userId}.png`; // Always PNG after processing

  // Upload to Supabase Storage
  const { data, error } = await supabase.storage
    .from(AVATAR_BUCKET)
    .upload(fileName, processedFile, {
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
 * Shows cropped preview (square, 200x200px).
 */
export function createAvatarPreview(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const reader = new FileReader();

    reader.onload = (e) => {
      img.onload = () => {
        // Calculate square crop
        const size = Math.min(img.width, img.height);
        const x = (img.width - size) / 2;
        const y = (img.height - size) / 2;

        const canvas = document.createElement("canvas");
        canvas.width = 200; // Preview size
        canvas.height = 200;
        const ctx = canvas.getContext("2d");

        if (!ctx) {
          reject(new Error("Kon preview niet maken"));
          return;
        }

        ctx.drawImage(img, x, y, size, size, 0, 0, 200, 200);
        resolve(canvas.toDataURL("image/png"));
      };

      img.onerror = () => reject(new Error("Kon afbeelding niet laden"));
      img.src = e.target?.result as string;
    };

    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

