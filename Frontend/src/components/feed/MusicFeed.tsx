// Frontend/src/components/feed/MusicFeed.tsx
import { useNewsFeed } from "@/hooks/useNewsFeed";
import { NewsCountrySelector } from "@/components/news/NewsCountrySelector";
import { NewsList } from "@/components/news/NewsList";
import { useState, useEffect } from "react";
import { cn } from "@/lib/ui/cn";

export interface MusicFeedProps {
  className?: string;
}

export function MusicFeed({ className }: MusicFeedProps) {
  const [musicCountry, setMusicCountry] = useState<"nl" | "tr">("tr");

  // Read music_country from hash on mount
  useEffect(() => {
    const hashParams = (() => {
      if (typeof window === "undefined") return new URLSearchParams();
      const hash = window.location.hash ?? "";
      const queryIndex = hash.indexOf("?");
      const query = queryIndex >= 0 ? hash.slice(queryIndex + 1) : "";
      return new URLSearchParams(query);
    })();
    const hashMusicCountry = hashParams.get("music_country") as "nl" | "tr" | null;
    if (hashMusicCountry === "nl" || hashMusicCountry === "tr") {
      setMusicCountry(hashMusicCountry);
    }
  }, []);

  // Update hash when musicCountry changes
  useEffect(() => {
    const hashParams = (() => {
      if (typeof window === "undefined") return new URLSearchParams();
      const hash = window.location.hash ?? "";
      const queryIndex = hash.indexOf("?");
      const query = queryIndex >= 0 ? hash.slice(queryIndex + 1) : "";
      return new URLSearchParams(query);
    })();
    hashParams.set("music_country", musicCountry);
    const base = window.location.hash.split("?")[0] || "#/feed";
    const query = hashParams.toString();
    window.location.hash = query ? `${base}?${query}` : base;
  }, [musicCountry]);

  const {
    items,
    isLoading,
    isLoadingMore,
    error,
    hasMore,
    reload,
    loadMore,
    meta,
  } = useNewsFeed({
    feed: "music",
    pageSize: 20,
    musicCountry,
  });

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <NewsCountrySelector
        value={musicCountry}
        onChange={setMusicCountry}
        className="mt-2 mb-2"
      />
      <NewsList
        items={items}
        isLoading={isLoading}
        isLoadingMore={isLoadingMore}
        error={error}
        hasMore={hasMore}
        onReload={reload}
        onLoadMore={loadMore}
        emptyMessage="Geen tracks beschikbaar"
        errorMessage={meta?.unavailable_reason ? "Muziek is momenteel niet beschikbaar" : undefined}
      />
    </div>
  );
}

