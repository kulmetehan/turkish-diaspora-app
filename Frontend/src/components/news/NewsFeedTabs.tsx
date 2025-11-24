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
      <TabsList className="flex w-full overflow-x-auto rounded-2xl border border-border bg-surface-muted p-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground shadow-inner sm:text-sm">
        {NEWS_FEEDS.map((feed) => (
          <TabsTrigger
            key={feed.key}
            value={feed.key}
            className="flex-1 min-w-[96px] whitespace-nowrap rounded-xl px-3 py-1.5 text-foreground transition-all duration-200 data-[state=active]:bg-[hsl(var(--brand-red-strong))] data-[state=active]:text-brand-white data-[state=active]:shadow-[0_12px_30px_rgba(0,0,0,0.35)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            {feed.label}
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  );
}


