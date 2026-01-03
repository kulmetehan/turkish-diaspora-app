// Frontend/src/components/prikbord/PrikbordComposer.tsx
import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/ui/cn";
import { createSharedLink, previewUrl, type UrlPreviewData } from "@/lib/api/prikbord";
import type { SharedLink } from "@/types/prikbord";
import { uploadMedia, createMediaPreview, type MediaUploadResult } from "@/lib/mediaUpload";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { URLPreview } from "./URLPreview";
import { useTranslation } from "@/hooks/useTranslation";
import postBot from "@/assets/post.png";

interface PrikbordComposerProps {
  onSuccess?: (newPost?: SharedLink) => void;
  className?: string;
}

const URL_REGEX = /(https?:\/\/[^\s]+)/g;

export function PrikbordComposer({ onSuccess, className }: PrikbordComposerProps) {
  const { t } = useTranslation();
  const [text, setText] = useState("");
  const [isExpanded, setIsExpanded] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [urlPreview, setUrlPreview] = useState<UrlPreviewData | null>(null);
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const [mediaFiles, setMediaFiles] = useState<File[]>([]);
  const [mediaPreviews, setMediaPreviews] = useState<string[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isPosting, setIsPosting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const previewTimeoutRef = useRef<number | null>(null);

  // Detect URLs in text and fetch preview
  useEffect(() => {
    if (previewTimeoutRef.current) {
      clearTimeout(previewTimeoutRef.current);
    }

    const matches = text.match(URL_REGEX);
    if (matches && matches.length > 0) {
      const url = matches[0];
      setIsLoadingPreview(true);
      
      previewTimeoutRef.current = window.setTimeout(async () => {
        try {
          const preview = await previewUrl(url);
          setUrlPreview(preview);
        } catch (error) {
          console.error("Failed to fetch URL preview:", error);
          // Don't show error to user, just continue without preview
          setUrlPreview(null);
        } finally {
          setIsLoadingPreview(false);
        }
      }, 500); // Debounce 500ms
    } else {
      setUrlPreview(null);
      setIsLoadingPreview(false);
    }

    return () => {
      if (previewTimeoutRef.current) {
        clearTimeout(previewTimeoutRef.current);
      }
    };
  }, [text]);

  const handleFileSelect = async (files: FileList | null) => {
    if (!files || files.length === 0) return;

    const newFiles = Array.from(files);
    const newPreviews: string[] = [];

    for (const file of newFiles) {
      try {
        const preview = await createMediaPreview(file);
        newPreviews.push(preview);
      } catch (error) {
        console.error("Failed to create preview:", error);
        toast.error(`Kon preview niet maken voor ${file.name}`);
      }
    }

    setMediaFiles((prev) => [...prev, ...newFiles]);
    setMediaPreviews((prev) => [...prev, ...newPreviews]);
  };

  const removeMedia = (index: number) => {
    setMediaFiles((prev) => prev.filter((_, i) => i !== index));
    setMediaPreviews((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async () => {
    // Validate: need at least text, URL, or media
    const hasText = text.trim().length > 0;
    const hasUrl = urlPreview !== null;
    const hasMedia = mediaFiles.length > 0;

    if (!hasText && !hasUrl && !hasMedia) {
      toast.error("Voeg tekst, een link of media toe");
      return;
    }

    setIsSubmitting(true);
    setIsUploading(hasMedia);
    setIsPosting(false);
    setUploadProgress(0);

    try {
      // Upload media files if any
      let mediaUrls: string[] = [];
      if (mediaFiles.length > 0) {
        // Track upload progress
        const totalFiles = mediaFiles.length;
        let completedFiles = 0;
        
        const uploadPromises = mediaFiles.map(async (file, index) => {
          const result = await uploadMedia(file);
          completedFiles++;
          setUploadProgress(Math.round((completedFiles / totalFiles) * 100));
          return result;
        });
        
        const uploadResults = await Promise.all(uploadPromises);
        mediaUrls = uploadResults.map((result) => result.url);
      }

      setIsUploading(false);
      setIsPosting(true);

      // Extract URL from text if present
      const urlMatches = text.match(URL_REGEX);
      const url = urlMatches && urlMatches.length > 0 ? urlMatches[0] : undefined;

      // Determine post type
      let postType: "link" | "media" | "text";
      if (mediaUrls.length > 0) {
        postType = "media";
      } else if (hasUrl) {
        postType = "link";
      } else if (hasText) {
        postType = "text";
      } else {
        throw new Error("Geen content om te delen");
      }

      // Prepare title and description from user text
      const textLines = text.trim().split('\n');
      const userTitle = textLines[0] || undefined;
      const userDescription = text.trim() || undefined;

      // For media and text posts, use user text ONLY in description (Facebook-style)
      // For link posts, prefer URL preview but allow user text override
      let title: string | undefined;
      let description: string | undefined;

      if (postType === "media") {
        // Media posts: use user text ONLY in description (Facebook-style)
        title = undefined;  // Don't set title for media posts
        description = userDescription;
      } else if (postType === "link") {
        // Link posts: prefer URL preview, but allow user text override
        title = urlPreview?.title || userTitle;
        description = urlPreview?.description || userDescription;
      } else {
        // Text posts: use user text ONLY in description (Facebook-style)
        title = undefined;  // Don't set title for text posts
        description = userDescription;
      }

      // Create post
      const newPost = await createSharedLink({
        url: url,
        post_type: postType,
        media_urls: mediaUrls,
        title: title,
        description: description,
        image_url: urlPreview?.image_url || undefined,
      });

      toast.success("Post gedeeld!");
      
      // Reset form
      setText("");
      setUrlPreview(null);
      setMediaFiles([]);
      setMediaPreviews([]);
      setIsExpanded(false);
      setUploadProgress(0);
      
      // Pass new post to callback for optimistic update
      onSuccess?.(newPost);
    } catch (error: any) {
      toast.error("Kon post niet delen", {
        description: error.message || "Er is een fout opgetreden",
      });
    } finally {
      setIsSubmitting(false);
      setIsUploading(false);
      setIsPosting(false);
      setUploadProgress(0);
    }
  };

  const canSubmit = text.trim().length > 0 || urlPreview !== null || mediaFiles.length > 0;

  return (
    <div className={cn("rounded-xl border border-border/50 bg-card p-4 shadow-soft", className)}>
      <div className="space-y-3">
        {/* Textarea with mascot image */}
        <div className="relative">
          <Textarea
            placeholder="Wat wil je delen?"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onFocus={() => setIsExpanded(true)}
            rows={isExpanded ? 4 : 2}
            className="resize-none font-gilroy pr-24"
            disabled={isSubmitting}
          />
          {/* Mascot image - positioned on the right side, matching textarea height */}
          <div className="absolute right-2 top-2 bottom-2 pointer-events-none flex items-center justify-end">
            <img
              src={postBot}
              alt=""
              className="h-full max-h-full object-contain"
            />
          </div>
        </div>

        {/* URL Preview */}
        {isLoadingPreview && (
          <div className="rounded-lg border border-border bg-card p-3">
            <p className="text-xs text-muted-foreground">Preview laden...</p>
          </div>
        )}
        {urlPreview && !isLoadingPreview && (
          <URLPreview preview={urlPreview} onRemove={() => setUrlPreview(null)} />
        )}

        {/* Media Previews */}
        {mediaPreviews.length > 0 && (
          <div className="grid grid-cols-2 gap-2">
            {mediaPreviews.map((preview, index) => {
              const file = mediaFiles[index];
              const isVideo = file?.type.startsWith("video/");
              return (
                <div key={index} className="relative group">
                  {isVideo ? (
                    <video
                      src={preview}
                      className="w-full h-32 object-cover rounded-lg"
                      controls={false}
                    />
                  ) : (
                    <img
                      src={preview}
                      alt={`Preview ${index + 1}`}
                      className="w-full h-32 object-cover rounded-lg"
                    />
                  )}
                  <button
                    type="button"
                    onClick={() => removeMedia(index)}
                    className="absolute top-1 right-1 bg-destructive text-destructive-foreground rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                    disabled={isSubmitting}
                  >
                    <Icon name="X" className="h-3 w-3" />
                  </button>
                </div>
              );
            })}
          </div>
        )}

        {/* Progress Indicator */}
        {(isUploading || isPosting) && (
          <div className="rounded-lg border border-border bg-card p-3 space-y-2">
            {isUploading && (
              <>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Uploaden...</span>
                  <span className="text-muted-foreground">{uploadProgress}%</span>
                </div>
                <div className="w-full bg-muted rounded-full h-2">
                  <div
                    className="bg-primary h-2 rounded-full transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </>
            )}
            {isPosting && !isUploading && (
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Icon name="Loader2" className="h-3 w-3 animate-spin" />
                <span>Posten...</span>
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            {/* Media upload button */}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isSubmitting}
              className="flex items-center justify-center h-9 w-9 rounded-full text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
              aria-label="Media uploaden"
            >
              <Icon name="Image" className="h-5 w-5" />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="image/*,video/*"
              onChange={(e) => handleFileSelect(e.target.files)}
              className="hidden"
              disabled={isSubmitting}
            />
          </div>

          <Button
            onClick={handleSubmit}
            disabled={!canSubmit || isSubmitting || isUploading || isPosting}
            size="sm"
            className="gap-1.5"
          >
            {isSubmitting || isUploading || isPosting ? (
              <>
                <Icon name="Loader2" className="h-4 w-4 animate-spin" />
                {isUploading ? `Uploaden... ${uploadProgress}%` : isPosting ? "Posten..." : "Delen..."}
              </>
            ) : (
              <>
                <Icon name="Send" className="h-4 w-4" />
                Delen
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

