// Frontend/src/components/prikbord/URLPreview.tsx
import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/ui/cn";
import type { UrlPreviewData } from "@/lib/api/prikbord";

interface URLPreviewProps {
  preview: UrlPreviewData;
  onRemove: () => void;
  className?: string;
}

export function URLPreview({ preview, onRemove, className }: URLPreviewProps) {
  return (
    <div className={cn("relative rounded-lg border border-border bg-card p-3", className)}>
      <button
        type="button"
        onClick={onRemove}
        className="absolute right-2 top-2 flex h-6 w-6 items-center justify-center rounded-full bg-background/80 text-muted-foreground hover:bg-background hover:text-foreground transition-colors"
        aria-label="Verwijder preview"
      >
        <Icon name="X" className="h-3 w-3" />
      </button>

      <div className="flex gap-3 pr-8">
        {preview.image_url && (
          <div className="flex-shrink-0 overflow-hidden rounded border border-border/70 bg-muted h-20 w-20">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={preview.image_url}
              alt=""
              className="h-full w-full object-cover"
            />
          </div>
        )}

        <div className="flex-1 min-w-0">
          {preview.title && (
            <p className="text-sm font-gilroy font-medium leading-tight line-clamp-2 mb-1">
              {preview.title}
            </p>
          )}
          {preview.description && (
            <p className="text-xs font-gilroy font-normal text-muted-foreground line-clamp-2 mb-1">
              {preview.description}
            </p>
          )}
          <p className="text-xs font-gilroy font-normal text-muted-foreground/70">
            {preview.domain}
          </p>
        </div>
      </div>
    </div>
  );
}





