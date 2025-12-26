// Frontend/src/components/ui/EmojiPicker.tsx
import { cn } from "@/lib/ui/cn";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import EmojiPickerLib from "emoji-picker-react";
import { Icon } from "@/components/Icon";

export interface EmojiPickerProps {
  onEmojiSelect: (emoji: string) => void;
  trigger?: React.ReactNode;
  className?: string;
}

// Picker dimensions for positioning calculations
// Responsive: smaller on mobile
const getPickerDimensions = () => {
  if (typeof window === "undefined") return { width: 320, height: 320 };
  const isMobile = window.innerWidth < 640; // sm breakpoint
  const viewportHeight = window.innerHeight;
  
  // On mobile, use viewport height minus margins, but max 320px
  // Leave room for keyboard and margins
  const mobileHeight = Math.min(
    viewportHeight * 0.5, // 50% of viewport height
    320 // Max height
  );
  
  return {
    width: isMobile ? Math.min(window.innerWidth - 24, 300) : 320, // Smaller width
    height: isMobile ? mobileHeight : 320, // Smaller height
  };
};

const PICKER_OFFSET = 8; // Margin between trigger and picker
const VIEWPORT_MARGIN = 12; // Minimum margin from viewport edges

type Position = {
  vertical: "top" | "bottom";
  horizontal: "left" | "right";
  top: number;
  left: number;
};

export function EmojiPicker({ onEmojiSelect, trigger, className }: EmojiPickerProps) {
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState<Position>({
    vertical: "bottom",
    horizontal: "left",
    top: 0,
    left: 0,
  });
  const pickerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLDivElement>(null);
  const [mounted, setMounted] = useState(false);

  // Detect dark mode
  const isDark = typeof document !== "undefined" && document.documentElement.classList.contains("dark");

  // Mount check for portal
  useEffect(() => {
    setMounted(true);
  }, []);

  // Prevent mobile keyboard on search field
  useEffect(() => {
    if (!open || !mounted) return;
    
    const preventKeyboard = () => {
      const searchInput = document.querySelector('.emoji-picker-wrapper .epr-search-container input') as HTMLInputElement;
      if (searchInput && window.innerWidth < 640) {
        // Prevent keyboard on mobile
        searchInput.setAttribute('inputmode', 'none');
        searchInput.setAttribute('readonly', 'true');
        // Remove readonly on blur to allow typing if user really wants to
        const handleBlur = () => {
          searchInput.removeAttribute('readonly');
        };
        searchInput.addEventListener('blur', handleBlur, { once: true });
      }
    };

    // Small delay to ensure DOM is ready
    const timeout = setTimeout(preventKeyboard, 100);
    return () => clearTimeout(timeout);
  }, [open, mounted]);

  // Calculate position based on viewport with improved logic
  useEffect(() => {
    if (!open || !triggerRef.current || !pickerRef.current) return;

    const updatePosition = () => {
      const triggerRect = triggerRef.current?.getBoundingClientRect();
      if (!triggerRect) return;

      const pickerDimensions = getPickerDimensions();
      const PICKER_WIDTH = pickerDimensions.width;
      const PICKER_HEIGHT = pickerDimensions.height;

      const viewport = {
        width: window.innerWidth,
        height: window.innerHeight,
      };

      // Calculate available space
      const spaceAbove = triggerRect.top;
      const spaceBelow = viewport.height - triggerRect.bottom;
      const spaceLeft = triggerRect.left;
      const spaceRight = viewport.width - triggerRect.right;

      // Determine vertical position - prefer bottom unless there's not enough space
      // Only use top if there's significantly more space above than below
      const verticalPosition: "top" | "bottom" =
        spaceBelow >= PICKER_HEIGHT + VIEWPORT_MARGIN
          ? "bottom" // Prefer bottom if there's enough space
          : spaceAbove >= PICKER_HEIGHT + VIEWPORT_MARGIN && spaceAbove > spaceBelow * 1.5
          ? "top" // Only use top if there's much more space above
          : "bottom"; // Default to bottom even if tight

      // Determine horizontal position
      // Try to align left edge with trigger left edge, but adjust if needed
      let horizontalPosition: "left" | "right" = "left";
      let offsetX = 0;

      if (spaceRight >= PICKER_WIDTH + VIEWPORT_MARGIN) {
        // Enough space on the right, align left
        horizontalPosition = "left";
        offsetX = 0;
      } else if (spaceLeft >= PICKER_WIDTH + VIEWPORT_MARGIN) {
        // Not enough space on right, but enough on left - align right
        horizontalPosition = "right";
        offsetX = 0;
      } else {
        // Not enough space on either side - center relative to trigger
        const triggerCenter = triggerRect.left + triggerRect.width / 2;
        const pickerCenter = PICKER_WIDTH / 2;
        
        if (triggerCenter - pickerCenter < VIEWPORT_MARGIN) {
          // Too far left, align to left edge
          horizontalPosition = "left";
          offsetX = -(triggerRect.left - VIEWPORT_MARGIN);
        } else if (triggerCenter + pickerCenter > viewport.width - VIEWPORT_MARGIN) {
          // Too far right, align to right edge
          horizontalPosition = "right";
          offsetX = viewport.width - VIEWPORT_MARGIN - (triggerRect.right - PICKER_WIDTH);
        } else {
          // Center on trigger
          horizontalPosition = "left";
          offsetX = triggerRect.width / 2 - pickerCenter;
        }
      }

      // Calculate fixed position (relative to viewport)
      let top = 0;
      let left = 0;

      if (verticalPosition === "bottom") {
        // Position below trigger with offset
        top = triggerRect.bottom + PICKER_OFFSET;
      } else {
        // Position above trigger, but ensure we don't cover the trigger
        // Position above with enough space so trigger remains visible
        top = triggerRect.top - PICKER_HEIGHT - PICKER_OFFSET;
        // If this would cover the trigger, adjust to show trigger at bottom of picker
        if (top + PICKER_HEIGHT > triggerRect.top) {
          top = triggerRect.top - PICKER_HEIGHT;
        }
      }

      if (horizontalPosition === "left") {
        left = triggerRect.left + offsetX;
      } else {
        left = triggerRect.right - PICKER_WIDTH + offsetX;
      }

      // Constrain to viewport
      if (left < VIEWPORT_MARGIN) {
        left = VIEWPORT_MARGIN;
      } else if (left + PICKER_WIDTH > viewport.width - VIEWPORT_MARGIN) {
        left = viewport.width - PICKER_WIDTH - VIEWPORT_MARGIN;
      }

      // Ensure picker doesn't cover the trigger when positioned above
      if (verticalPosition === "top" && top + PICKER_HEIGHT > triggerRect.top - PICKER_OFFSET) {
        // If picker would cover trigger, switch to bottom position
        top = triggerRect.bottom + PICKER_OFFSET;
      }

      // On mobile, ensure picker doesn't overflow viewport
      const isMobile = viewport.width < 640;
      const maxTop = isMobile 
        ? VIEWPORT_MARGIN // Small margin at top on mobile
        : VIEWPORT_MARGIN;
      const maxBottom = isMobile
        ? viewport.height * 0.85 // Leave 15% margin at bottom on mobile (room for keyboard)
        : viewport.height - VIEWPORT_MARGIN;

      if (top < maxTop) {
        top = maxTop;
      } else if (top + PICKER_HEIGHT > maxBottom) {
        top = maxBottom - PICKER_HEIGHT;
        // If still too tall, constrain height
        if (top < maxTop) {
          top = maxTop;
          if (pickerRef.current) {
            pickerRef.current.style.maxHeight = `${maxBottom - top}px`;
          }
        }
      }

      // Constrain picker height if needed
      const maxHeight =
        verticalPosition === "bottom"
          ? spaceBelow - PICKER_OFFSET - VIEWPORT_MARGIN
          : spaceAbove - PICKER_OFFSET - VIEWPORT_MARGIN;

      setPosition({
        vertical: verticalPosition,
        horizontal: horizontalPosition,
        top,
        left,
      });

      // Apply max height constraint if picker would overflow
      if (pickerRef.current && maxHeight < PICKER_HEIGHT) {
        pickerRef.current.style.maxHeight = `${Math.max(maxHeight, 200)}px`;
      } else if (pickerRef.current) {
        pickerRef.current.style.maxHeight = "";
      }
    };

    // Initial calculation
    updatePosition();

    // Update on scroll and resize
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

    // Also close on Escape key
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside, true);
    document.addEventListener("keydown", handleEscape, true);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside, true);
      document.removeEventListener("keydown", handleEscape, true);
    };
  }, [open]);

  const handleEmojiClick = (emojiData: any) => {
    console.log('EmojiPicker: Click received', emojiData);
    
    // emoji-picker-react passes an object with emoji property
    // Handle both possible API formats
    let emoji: string | null = null;
    
    if (typeof emojiData === 'string') {
      emoji = emojiData;
    } else if (emojiData?.emoji) {
      emoji = emojiData.emoji;
    } else if (emojiData?.unified) {
      // Convert unified code to emoji if needed
      try {
        emoji = String.fromCodePoint(...emojiData.unified.split('-').map((hex: string) => parseInt(hex, 16)));
      } catch (e) {
        console.error('Failed to convert unified emoji code:', e);
      }
    }
    
    console.log('EmojiPicker: Extracted emoji', emoji);
    
    if (emoji) {
      console.log('EmojiPicker: Calling onEmojiSelect with', emoji);
      onEmojiSelect(emoji);
      setOpen(false);
    } else {
      console.warn('EmojiPicker: Could not extract emoji from data:', emojiData);
    }
  };

  return (
    <div className="relative inline-block" onClick={(e) => e.stopPropagation()}>
      <div
        ref={triggerRef}
        onClick={(e) => {
          e.stopPropagation();
          setOpen(!open);
        }}
      >
        {trigger || (
          <button
            type="button"
            className={cn(
              "flex items-center justify-center",
              "h-7 w-7 rounded-md",
              "border border-border/50 bg-transparent",
              "hover:bg-muted hover:border-border",
              "transition-colors",
              "focus:outline-none focus:ring-2 focus:ring-primary/30",
              className
            )}
            aria-label="Add emoji reaction"
          >
            <Icon name="Plus" className="h-4 w-4 text-muted-foreground" />
          </button>
        )}
      </div>
      {open && mounted && createPortal(
        <div
          ref={pickerRef}
          className={cn(
            "fixed z-[9999]",
            "bg-card border border-border rounded-lg shadow-lg"
          )}
          style={{
            top: `${position.top}px`,
            left: `${position.left}px`,
            width: `${getPickerDimensions().width}px`,
            height: `${getPickerDimensions().height}px`,
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="emoji-picker-wrapper h-full overflow-hidden [&_.EmojiPickerReact]:!border-0 [&_.EmojiPickerReact]:!shadow-none">
            <EmojiPickerLib
              onEmojiClick={handleEmojiClick}
              searchPlaceHolder="Zoek emoji..."
              height={getPickerDimensions().height}
              width={getPickerDimensions().width}
              previewConfig={{ showPreview: false }}
              theme={isDark ? "dark" : "light"}
              skinTonesDisabled={false}
              lazyLoadEmojis={false}
              emojiStyle="native"
              autoFocusSearch={false}
              searchDisabled={false}
            />
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}
