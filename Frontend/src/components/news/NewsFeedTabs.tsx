import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/ui/cn";
import { NEWS_FEEDS, type NewsFeedKey } from "@/lib/routing/newsFeed";

export interface NewsFeedTabsProps {
  value: NewsFeedKey;
  onChange: (next: NewsFeedKey) => void;
  className?: string;
}

export function NewsFeedTabs({ value, onChange, className }: NewsFeedTabsProps) {
  return (
    <Tabs
      value={value}
      onValueChange={(next) => onChange(next as NewsFeedKey)}
      className={cn("w-full", className)}
    >
      <TabsList className="flex w-full overflow-x-auto rounded-xl bg-muted/80 p-1 text-muted-foreground">
        {NEWS_FEEDS.map((feed) => (
          <TabsTrigger
            key={feed.key}
            value={feed.key}
            className="flex-1 min-w-[96px] whitespace-nowrap px-3 py-1.5 text-xs font-medium transition-colors sm:text-sm"
          >
            {feed.label}
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  );
}

