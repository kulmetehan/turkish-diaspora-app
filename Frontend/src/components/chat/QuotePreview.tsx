// Frontend/src/components/chat/QuotePreview.tsx
import { cn } from "@/lib/ui/cn";
import type { ChatMessage } from "@/lib/api";
import { Icon } from "@/components/Icon";

interface QuotePreviewProps {
  message: ChatMessage;
  onClose?: () => void;
  className?: string;
}

export function QuotePreview({ message, onClose, className }: QuotePreviewProps) {
  const preview = message.content.length > 100 
    ? message.content.substring(0, 100) + "..."
    : message.content;

  return (
    <div className={cn(
      "flex items-start gap-2 p-2 rounded-lg bg-muted/50 border border-border",
      className
    )}>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-gilroy font-semibold text-muted-foreground">
            {message.user?.name || "Onbekend"}
          </span>
        </div>
        <p className="text-xs text-muted-foreground line-clamp-2">
          {preview}
        </p>
      </div>
      {onClose && (
        <button
          type="button"
          onClick={onClose}
          className="flex-shrink-0 p-1 rounded hover:bg-muted transition-colors"
          aria-label="Verwijder quote"
        >
          <Icon name="X" className="w-3 h-3" />
        </button>
      )}
    </div>
  );
}




