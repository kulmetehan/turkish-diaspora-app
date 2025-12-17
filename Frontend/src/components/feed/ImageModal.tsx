// Frontend/src/components/feed/ImageModal.tsx
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { X } from "lucide-react";
import { useEffect, useState } from "react";

interface ImageModalProps {
  imageUrl: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ImageModal({ imageUrl, open, onOpenChange }: ImageModalProps) {
  const [imageLoading, setImageLoading] = useState(true);
  const [imageError, setImageError] = useState(false);

  // Reset loading state when image changes
  useEffect(() => {
    if (imageUrl) {
      setImageLoading(true);
      setImageError(false);
    }
  }, [imageUrl]);

  // Handle Escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && open) {
        onOpenChange(false);
      }
    };

    if (open) {
      document.addEventListener("keydown", handleEscape);
      // Prevent body scroll when modal is open
      document.body.style.overflow = "hidden";
    }

    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "";
    };
  }, [open, onOpenChange]);

  if (!imageUrl) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-[90vw] max-h-[90vh] w-auto h-auto p-0 bg-black/95 border-none"
        overlayClassName="bg-black/80"
        onInteractOutside={(e) => {
          // Allow backdrop click to close
          e.preventDefault();
          onOpenChange(false);
        }}
      >
        <div className="relative w-full h-full flex items-center justify-center">
          {imageLoading && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-8 h-8 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            </div>
          )}
          {imageError ? (
            <div className="flex flex-col items-center justify-center p-8 text-white">
              <p className="text-sm">Afbeelding kon niet worden geladen</p>
            </div>
          ) : (
            <img
              src={imageUrl}
              alt=""
              className="max-w-[90vw] max-h-[90vh] w-auto h-auto object-contain"
              onLoad={() => setImageLoading(false)}
              onError={() => {
                setImageLoading(false);
                setImageError(true);
              }}
            />
          )}
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            className="absolute right-4 top-4 rounded-full bg-black/50 hover:bg-black/70 p-2 text-white transition-colors focus:outline-none focus:ring-2 focus:ring-white/50"
            aria-label="Sluiten"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

