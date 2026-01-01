// Frontend/src/components/news/NewsFeedTabs.tsx
import { NEWS_FEEDS, type NewsFeedKey } from "@/lib/routing/newsFeed";
import { cn } from "@/lib/ui/cn";
import { useTranslation } from "@/hooks/useTranslation";

export interface NewsFeedTabsProps {
  value: NewsFeedKey;
  onChange: (next: NewsFeedKey) => void;
  className?: string;
}

export function NewsFeedTabs({ value, onChange, className }: NewsFeedTabsProps) {
  const { t } = useTranslation();
  
  return (
    <div
      className={cn(
        "flex gap-2 overflow-x-auto px-4 py-2",
        className
      )}
      style={{
        scrollbarWidth: "none", // Firefox
        msOverflowStyle: "none", // IE/Edge
      }}
    >
      {NEWS_FEEDS.map((feed) => {
        const isActive = value === feed.key;
        const label = t(feed.labelKey);
        return (
          <button
            key={feed.key}
            type="button"
            onClick={() => onChange(feed.key)}
            className={cn(
              "flex-shrink-0 rounded-sm px-4 py-1.5 text-sm font-gilroy font-medium transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2",
              isActive
                ? "bg-primary text-primary-foreground shadow-soft"
                : "bg-gray-100 text-black hover:bg-gray-200"
            )}
            aria-pressed={isActive}
            aria-label={`Filter by ${label}`}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}


