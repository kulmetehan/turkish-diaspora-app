import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { surfaceTabsList, surfaceTabsTrigger } from "@/components/ui/tabStyles";
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
      <TabsList className={cn(surfaceTabsList, "overflow-x-auto bg-card")}>
        {NEWS_FEEDS.map((feed) => (
          <TabsTrigger
            key={feed.key}
            value={feed.key}
            className={surfaceTabsTrigger}
          >
            {feed.label}
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  );
}


