// Frontend/src/components/ui/EmojiPicker.tsx
import { cn } from "@/lib/ui/cn";
import { useEffect, useRef, useState } from "react";

export interface EmojiPickerProps {
  onEmojiSelect: (emoji: string) => void;
  trigger?: React.ReactNode;
  className?: string;
}

// Common emoji set for quick selection
const QUICK_EMOJIS = [
  "👍", "❤️", "🔥", "😊", "⭐", "🚩", "🎉", "💯",
  "🙏", "👏", "💪", "🎊", "✨", "🌟", "😍", "😂",
  "😮", "😢", "😡", "🤔", "👀", "💬", "📢", "🎯"
];

// Top 5 most used comment emojis for the trigger button
const TOP_5_EMOJIS = ["👍", "❤️", "🔥", "😊", "⭐"];

const PICKER_HEIGHT = 280; // Approximate height
const PICKER_OFFSET = 8; // mb-2 = 8px

export function EmojiPicker({ onEmojiSelect, trigger, className }: EmojiPickerProps) {
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState<"top" | "bottom">("top");
  const pickerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLDivElement>(null);

  // Calculate position based on viewport
  useEffect(() => {
    if (!open || !triggerRef.current) return;

    const updatePosition = () => {
      const triggerRect = triggerRef.current?.getBoundingClientRect();
      if (!triggerRect) return;

      const spaceAbove = triggerRect.top;
      const spaceBelow = window.innerHeight - triggerRect.bottom;
      const neededSpace = PICKER_HEIGHT + PICKER_OFFSET;

      // Position below if there's more space below and not enough space above
      if (spaceBelow >= neededSpace || (spaceBelow > spaceAbove && spaceBelow >= PICKER_HEIGHT * 0.6)) {
        setPosition("bottom");
      } else {
        setPosition("top");
      }
    };

    updatePosition();
    window.addEventListener("scroll", updatePosition, true);
    window.addEventListener("resize", updatePosition);

    return () => {
      window.removeEventListener("scroll", updatePosition, true);
      window.removeEventListener("resize", updatePosition);
    };
  }, [open]);

  // Close picker when clicking outside
  useEffect(() => {
    if (!open) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (
        pickerRef.current &&
        !pickerRef.current.contains(event.target as Node) &&
        triggerRef.current &&
        !triggerRef.current.contains(event.target as Node)
      ) {
        setOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside, true);
    return () => document.removeEventListener("mousedown", handleClickOutside, true);
  }, [open]);

  const handleQuickEmojiClick = (e: React.MouseEvent, emoji: string) => {
    e.stopPropagation();
    onEmojiSelect(emoji);
    setOpen(false);
  };

  return (
    <div className="relative inline-block" onClick={(e) => e.stopPropagation()}>
      <div ref={triggerRef} onClick={(e) => {
        e.stopPropagation();
        setOpen(!open);
      }}>
        {trigger || (
          <button
            type="button"
            className={cn(
              "flex items-center gap-1 h-7 px-2 text-xs rounded-lg transition-all",
              "bg-primary/10 text-primary border border-primary/30",
              "hover:bg-primary/15 focus:outline-none focus:ring-2 focus:ring-primary/30",
              className
            )}
            aria-label="Add emoji reaction"
          >
            <span className="text-sm mr-1">
              {TOP_5_EMOJIS.join("")}
            </span>
            <span>Reageer</span>
          </button>
        )}
      </div>
      {open && (
        <div
          ref={pickerRef}
          className={cn(
            "absolute left-0 z-50 w-80 p-4 bg-card border border-border rounded-lg shadow-lg",
            position === "top" ? "bottom-full mb-2" : "top-full mt-2"
          )}
        >
          <div className="grid grid-cols-8 gap-2">
            {QUICK_EMOJIS.map((emoji) => (
              <button
                key={emoji}
                type="button"
                onClick={(e) => handleQuickEmojiClick(e, emoji)}
                className={cn(
                  "text-2xl p-2 rounded-lg hover:bg-muted transition-colors",
                  "focus:outline-none focus:ring-2 focus:ring-primary/30"
                )}
                aria-label={`Select ${emoji}`}
              >
                {emoji}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
