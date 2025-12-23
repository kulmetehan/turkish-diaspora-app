// Frontend/src/components/news/NewsHeaderSearch.tsx
import { useEffect, useRef } from "react";

import { FloatingSearchBar } from "@/components/search/FloatingSearchBar";
import { cn } from "@/lib/ui/cn";

export interface NewsHeaderSearchProps {
  isOpen: boolean;
  value: string;
  onChange: (value: string) => void;
  onClear: () => void;
  onClose: () => void;
  loading?: boolean;
  className?: string;
}

export function NewsHeaderSearch({
  isOpen,
  value,
  onChange,
  onClear,
  onClose,
  loading,
  className,
}: NewsHeaderSearchProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input when opened
  useEffect(() => {
    if (isOpen && inputRef.current) {
      // Small delay to ensure animation completes
      const timer = setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  // Handle escape key to close
  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className={cn(
        "absolute inset-x-0 top-0 z-20 bg-surface-base px-4 pt-[max(0.75rem,env(safe-area-inset-top))] pb-3",
        "transition-all duration-300 ease-in-out",
        className
      )}
    >
      <div className="flex items-center gap-3">
        <FloatingSearchBar
          value={value}
          onValueChange={onChange}
          onClear={() => {
            onClear();
            if (!value.trim()) {
              onClose();
            }
          }}
          loading={loading}
          ariaLabel="Zoek nieuwsartikelen"
          placeholder="Zoek in diaspora nieuws…"
          className="flex-1"
        />
        <button
          type="button"
          onClick={onClose}
          className={cn(
            "flex h-11 w-11 items-center justify-center rounded-full",
            "text-muted-foreground transition-colors",
            "hover:bg-muted hover:text-foreground",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2"
          )}
          aria-label="Sluit zoeken"
        >
          <span className="text-lg">✕</span>
        </button>
      </div>
    </div>
  );
}








