// Frontend/src/components/feed/DashboardOverview.tsx
import type { EventItem } from "@/api/events";
import { fetchNews, type NewsItem } from "@/api/news";
import { Skeleton } from "@/components/ui/skeleton";
import {
  fetchCuratedEvents,
  fetchCuratedNews,
  fetchLocationStats,
  getActivityFeed,
  type ActivityItem,
  type CategoryStat,
} from "@/lib/api";
import { humanizeCategoryLabel } from "@/lib/categories";
import { getCategoryIcon } from "@/lib/map/marker-icons";
import { cn } from "@/lib/ui/cn";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { DashboardCard } from "./DashboardCard";
import type { ActivityFilter } from "./FeedFilterTabs";

interface DashboardOverviewProps {
  className?: string;
}

/**
 * Official category labels as used on the map (from categories.yml).
 * These are the canonical Dutch labels with proper capitalization.
 */
const OFFICIAL_CATEGORY_LABELS: Record<string, string> = {
  restaurant: "Restaurant",
  bakery: "Bakkerij",
  supermarket: "Supermarkt",
  barber: "Kapper",
  mosque: "Moskee",
  travel_agency: "Reisbureau",
  butcher: "Slagerij",
  fast_food: "Fastfood",
  cafe: "Café",
  automotive: "Automotive",
  insurance: "Verzekering",
  tailor: "Kleermaker",
  events_venue: "Trouwzaal",
  community_centre: "Vereniging",
  clinic: "Medische Praktijk",
};

/**
 * Get the official category label for a category key.
 * Falls back to humanized version if not found in official mapping.
 */
function getOfficialCategoryLabel(categoryKey: string | null | undefined): string {
  if (!categoryKey) return "—";
  const normalized = categoryKey.toLowerCase().trim();
  return OFFICIAL_CATEGORY_LABELS[normalized] || humanizeCategoryLabel(categoryKey);
}

interface NewsCardData {
  items: NewsItem[];
  loading: boolean;
  error: boolean;
}

interface LocationsCardData {
  total: number | null;
  formattedText: string | null;
  categories: CategoryStat[];
  loading: boolean;
  error: boolean;
}

interface EventsCardData {
  items: EventItem[];
  total: number | null;
  loading: boolean;
  error: boolean;
}

interface ActivityCardData {
  checkInsToday: number;
  reactionsThisWeek: number;
  notesThisWeek: number;
  pollsThisWeek: number;
  favoritesThisWeek: number;
  bulletinThisWeek: number;
  loading: boolean;
  error: boolean;
}

export function DashboardOverview({ className }: DashboardOverviewProps) {
  const navigate = useNavigate();

  const [newsData, setNewsData] = useState<NewsCardData>({
    items: [],
    loading: true,
    error: false,
  });

  const [locationsData, setLocationsData] = useState<LocationsCardData>({
    total: null,
    formattedText: null,
    categories: [],
    loading: true,
    error: false,
  });

  const [eventsData, setEventsData] = useState<EventsCardData>({
    items: [],
    total: null,
    loading: true,
    error: false,
  });

  const [activityData, setActivityData] = useState<ActivityCardData>({
    checkInsToday: 0,
    reactionsThisWeek: 0,
    notesThisWeek: 0,
    pollsThisWeek: 0,
    favoritesThisWeek: 0,
    bulletinThisWeek: 0,
    loading: true,
    error: false,
  });

  const [trendsNl, setTrendsNl] = useState<NewsCardData>({
    items: [],
    loading: true,
    error: false,
  });

  const [trendsTr, setTrendsTr] = useState<NewsCardData>({
    items: [],
    loading: true,
    error: false,
  });

  // Fetch curated news data
  useEffect(() => {
    let cancelled = false;

    async function loadNews() {
      try {
        const response = await fetchCuratedNews();
        if (!cancelled) {
          let items = response.items || [];

          // If we have fewer than 3 items, pad with placeholder items
          while (items.length < 3) {
            items.push({
              id: -items.length - 1, // Negative ID for placeholders
              title: "Nieuws item wordt geladen...",
              snippet: null,
              source: "Komşu",
              published_at: new Date().toISOString(),
              url: "#",
              image_url: null,
              tags: [],
            });
          }

          setNewsData({
            items: items.slice(0, 3), // Ensure exactly 3 items
            loading: false,
            error: false,
          });
        }
      } catch (error) {
        console.error("Failed to load curated news:", error);
        if (!cancelled) {
          setNewsData((prev) => ({
            ...prev,
            loading: false,
            error: true,
          }));
        }
      }
    }

    loadNews();
    return () => {
      cancelled = true;
    };
  }, []);

  // Fetch location stats with formatted text
  useEffect(() => {
    let cancelled = false;

    async function loadLocations() {
      try {
        const response = await fetchLocationStats();
        if (!cancelled) {
          setLocationsData({
            total: response.total,
            formattedText: response.formatted_text,
            categories: response.categories || [],
            loading: false,
            error: false,
          });
        }
      } catch (error) {
        console.error("Failed to load location stats:", error);
        if (!cancelled) {
          setLocationsData((prev) => ({
            ...prev,
            loading: false,
            error: true,
          }));
        }
      }
    }

    loadLocations();
    return () => {
      cancelled = true;
    };
  }, []);

  // Fetch curated events data
  useEffect(() => {
    let cancelled = false;

    async function loadEvents() {
      try {
        const response = await fetchCuratedEvents();
        if (!cancelled) {
          setEventsData({
            items: response.items || [],
            total: response.meta.total_ranked || null,
            loading: false,
            error: false,
          });
        }
      } catch (error) {
        console.error("Failed to load curated events:", error);
        if (!cancelled) {
          setEventsData((prev) => ({
            ...prev,
            loading: false,
            error: true,
          }));
        }
      }
    }

    loadEvents();
    return () => {
      cancelled = true;
    };
  }, []);

  // Fetch activity data
  useEffect(() => {
    let cancelled = false;

    async function loadActivity() {
      try {
        const activities = await getActivityFeed(50, 0);
        if (!cancelled) {
          const now = new Date();
          const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
          const weekAgo = new Date(today);
          weekAgo.setDate(weekAgo.getDate() - 7);

          let checkInsToday = 0;
          let reactionsThisWeek = 0;
          let notesThisWeek = 0;
          let pollsThisWeek = 0;
          let favoritesThisWeek = 0;
          let bulletinThisWeek = 0;

          activities.forEach((activity: ActivityItem) => {
            const activityDate = new Date(activity.created_at);

            if (activity.activity_type === "check_in" && activityDate >= today) {
              checkInsToday++;
            }

            if (activity.activity_type === "reaction" && activityDate >= weekAgo) {
              reactionsThisWeek++;
            }

            if (activity.activity_type === "note" && activityDate >= weekAgo) {
              notesThisWeek++;
            }

            if (activity.activity_type === "poll_response" && activityDate >= weekAgo) {
              pollsThisWeek++;
            }

            if (activity.activity_type === "favorite" && activityDate >= weekAgo) {
              favoritesThisWeek++;
            }

            if (activity.activity_type === "bulletin_post" && activityDate >= weekAgo) {
              bulletinThisWeek++;
            }
          });

          setActivityData({
            checkInsToday,
            reactionsThisWeek,
            notesThisWeek,
            pollsThisWeek,
            favoritesThisWeek,
            bulletinThisWeek,
            loading: false,
            error: false,
          });
        }
      } catch (error) {
        console.error("Failed to load activity:", error);
        if (!cancelled) {
          setActivityData((prev) => ({
            ...prev,
            loading: false,
            error: true,
          }));
        }
      }
    }

    loadActivity();
    return () => {
      cancelled = true;
    };
  }, []);

  // Fetch trends for Netherlands
  useEffect(() => {
    let cancelled = false;
    let controller: AbortController | null = null;

    async function loadTrendsNl() {
      if (controller) {
        controller.abort();
      }
      controller = new AbortController();

      try {
        const response = await fetchNews({
          feed: "trending",
          trendCountry: "nl",
          limit: 10,
          signal: controller.signal,
        });
        if (!cancelled) {
          setTrendsNl({
            items: response.items || [],
            loading: false,
            error: false,
          });
        }
      } catch (error) {
        if (error instanceof Error && error.name === "AbortError") {
          return;
        }
        console.error("Failed to load trends NL:", error);
        if (!cancelled) {
          setTrendsNl((prev) => ({
            ...prev,
            loading: false,
            error: true,
          }));
        }
      }
    }

    loadTrendsNl();

    // Periodieke refresh elk uur
    const intervalId = setInterval(() => {
      if (!cancelled) {
        loadTrendsNl();
      }
    }, 3600000); // 1 uur

    return () => {
      cancelled = true;
      if (controller) {
        controller.abort();
      }
      clearInterval(intervalId);
    };
  }, []);

  // Fetch trends for Turkey
  useEffect(() => {
    let cancelled = false;
    let controller: AbortController | null = null;

    async function loadTrendsTr() {
      if (controller) {
        controller.abort();
      }
      controller = new AbortController();

      try {
        const response = await fetchNews({
          feed: "trending",
          trendCountry: "tr",
          limit: 10,
          signal: controller.signal,
        });
        if (!cancelled) {
          setTrendsTr({
            items: response.items || [],
            loading: false,
            error: false,
          });
        }
      } catch (error) {
        if (error instanceof Error && error.name === "AbortError") {
          return;
        }
        console.error("Failed to load trends TR:", error);
        if (!cancelled) {
          setTrendsTr((prev) => ({
            ...prev,
            loading: false,
            error: true,
          }));
        }
      }
    }

    loadTrendsTr();

    // Periodieke refresh elk uur
    const intervalId = setInterval(() => {
      if (!cancelled) {
        loadTrendsTr();
      }
    }, 3600000); // 1 uur

    return () => {
      cancelled = true;
      if (controller) {
        controller.abort();
      }
      clearInterval(intervalId);
    };
  }, []);

  // Format date helper
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("nl-NL", { day: "numeric", month: "short" });
  };

  // Navigate to feed with specific filter
  const navigateToFeedFilter = (filter: ActivityFilter) => {
    navigate("/feed", { state: { filter } });
  };

  return (
    <div className={cn("grid grid-cols-2 gap-3", className)}>
      {/* News Card */}
      <DashboardCard
        title="Laatste nieuws"
        icon="Newspaper"
        footerLink="/news"
        footerText="Bekijk alle nieuws"
      >
        {newsData.loading ? (
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-5/6" />
          </div>
        ) : newsData.error ? (
          <p className="text-xs font-gilroy font-normal">Niet beschikbaar</p>
        ) : newsData.items.length === 0 ? (
          <p className="text-xs font-gilroy font-normal">Geen nieuws beschikbaar</p>
        ) : (
          <div className="flex flex-col justify-center space-y-0 min-h-[80px]">
            {newsData.items.slice(0, 3).map((item, index) => (
              <div
                key={item.id}
                className={cn(
                  "space-y-0.5 py-1.5",
                  index < newsData.items.length - 1 && "border-b border-border/40"
                )}
              >
                <p className="line-clamp-1 text-[11px] font-gilroy font-medium leading-tight">
                  {item.title}
                </p>
                <p className="truncate text-[10px] font-gilroy font-normal text-muted-foreground/70">
                  {item.source} · {formatDate(item.published_at)}
                </p>
              </div>
            ))}
          </div>
        )}
      </DashboardCard>

      {/* Locations Card */}
      <DashboardCard
        title="In de buurt"
        icon="Map"
        footerLink="/map"
        footerText="Bekijk op kaart"
      >
        {locationsData.loading ? (
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </div>
        ) : locationsData.error ? (
          <p className="text-xs font-gilroy font-normal">Laden...</p>
        ) : locationsData.categories && locationsData.categories.length > 0 ? (
          <div className="flex flex-col justify-center space-y-0 min-h-[80px]">
            {locationsData.categories.slice(0, 3).map((cat, index) => {
              const Icon = getCategoryIcon(cat.category);
              const officialLabel = getOfficialCategoryLabel(cat.category);
              return (
                <div
                  key={cat.category}
                  className={cn(
                    "flex items-center gap-2 py-1.5",
                    index < Math.min(locationsData.categories.length, 3) - 1 && "border-b border-border/40"
                  )}
                >
                  <div className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded bg-primary/10 text-primary">
                    <Icon size={12} strokeWidth={2} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[11px] font-gilroy font-medium leading-tight truncate">
                      {officialLabel}
                    </p>
                    <p className="text-[10px] font-gilroy font-normal text-muted-foreground/70">
                      {cat.count.toLocaleString("nl-NL")} locaties
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        ) : locationsData.formattedText ? (
          <div className="space-y-1">
            <p className="text-xs font-gilroy font-normal leading-tight">
              {locationsData.formattedText}
            </p>
          </div>
        ) : locationsData.total !== null ? (
          <div className="space-y-1">
            <p className="text-xs font-gilroy font-normal">
              {locationsData.total.toLocaleString("nl-NL")} Turkse locaties in Nederland
            </p>
          </div>
        ) : (
          <p className="text-xs font-gilroy font-normal">Laden...</p>
        )}
      </DashboardCard>

      {/* Events Card */}
      <DashboardCard
        title="Events"
        icon="CalendarCheck"
        footerLink="/events"
        footerText="Bekijk alle events"
      >
        {eventsData.loading ? (
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-5/6" />
          </div>
        ) : eventsData.error ? (
          <p className="text-xs font-gilroy font-normal">Niet beschikbaar</p>
        ) : eventsData.items.length === 0 ? (
          <p className="text-xs font-gilroy font-normal">Geen events beschikbaar</p>
        ) : (
          <div className="flex flex-col justify-center space-y-0 min-h-[80px]">
            {eventsData.items.slice(0, 3).map((event, index) => (
              <div
                key={event.id}
                className={cn(
                  "space-y-0.5 py-1.5",
                  index < eventsData.items.length - 1 && "border-b border-border/40"
                )}
              >
                <p className="line-clamp-1 text-[11px] font-gilroy font-medium leading-tight">
                  {event.title}
                </p>
                <div className="flex items-center justify-between gap-2 text-[10px] font-gilroy font-normal text-muted-foreground/70">
                  <span className="flex-shrink-0">{formatDate(event.start_time_utc)}</span>
                  {event.location_text && (
                    <span className="line-clamp-1 truncate text-left">{event.location_text}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </DashboardCard>

      {/* Activity Summary Card */}
      <DashboardCard
        title="Activiteit"
        icon="Sparkles"
      >
        {activityData.loading ? (
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </div>
        ) : activityData.error ? (
          <p className="text-xs font-gilroy font-normal">Niet beschikbaar</p>
        ) : (
          <div className="space-y-1">
            <button
              onClick={() => navigateToFeedFilter("check_in")}
              className="w-full text-left text-xs font-gilroy font-medium text-primary transition-colors hover:text-primary/80"
            >
              {activityData.checkInsToday} check-ins vandaag
            </button>
            <button
              onClick={() => navigateToFeedFilter("reaction")}
              className="w-full text-left text-xs font-gilroy font-medium text-primary transition-colors hover:text-primary/80"
            >
              {activityData.reactionsThisWeek} reacties deze week
            </button>
            <button
              onClick={() => navigateToFeedFilter("note")}
              className="w-full text-left text-xs font-gilroy font-medium text-primary transition-colors hover:text-primary/80"
            >
              {activityData.notesThisWeek} notities deze week
            </button>
            <button
              onClick={() => navigateToFeedFilter("poll_response")}
              className="w-full text-left text-xs font-gilroy font-medium text-primary transition-colors hover:text-primary/80"
            >
              {activityData.pollsThisWeek} polls deze week
            </button>
            <button
              onClick={() => navigateToFeedFilter("favorite")}
              className="w-full text-left text-xs font-gilroy font-medium text-primary transition-colors hover:text-primary/80"
            >
              {activityData.favoritesThisWeek} favorieten deze week
            </button>
            <button
              onClick={() => navigateToFeedFilter("bulletin_post")}
              className="w-full text-left text-xs font-gilroy font-medium text-primary transition-colors hover:text-primary/80"
            >
              {activityData.bulletinThisWeek} advertenties deze week
            </button>
          </div>
        )}
      </DashboardCard>

      {/* Trending Netherlands Card */}
      <DashboardCard
        title="Top 10 Trending Nederland"
        icon="TrendingUp"
        footerLink="#/news?feed=trending&trend_country=nl"
        footerText="Bekijk alle trends"
      >
        {trendsNl.loading ? (
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-5/6" />
          </div>
        ) : trendsNl.error ? (
          <p className="text-xs font-gilroy font-normal">Niet beschikbaar</p>
        ) : trendsNl.items.length === 0 ? (
          <p className="text-xs font-gilroy font-normal">Geen trends beschikbaar</p>
        ) : (
          <div className="flex flex-col justify-center space-y-0 min-h-[80px]">
            {trendsNl.items.slice(0, 10).map((item, index) => (
              <div
                key={item.id}
                className={cn(
                  "flex items-center gap-2 py-1.5",
                  index < trendsNl.items.length - 1 && "border-b border-border/40"
                )}
              >
                <span className="flex-shrink-0 text-[11px] font-gilroy font-semibold text-muted-foreground/70 leading-none">
                  {index + 1}.
                </span>
                <p className="line-clamp-1 text-[11px] font-gilroy font-medium leading-tight flex-1">
                  {item.title}
                </p>
              </div>
            ))}
          </div>
        )}
      </DashboardCard>

      {/* Trending Turkey Card */}
      <DashboardCard
        title="Top 10 Trending Turkije"
        icon="TrendingUp"
        footerLink="#/news?feed=trending&trend_country=tr"
        footerText="Bekijk alle trends"
      >
        {trendsTr.loading ? (
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-5/6" />
          </div>
        ) : trendsTr.error ? (
          <p className="text-xs font-gilroy font-normal">Niet beschikbaar</p>
        ) : trendsTr.items.length === 0 ? (
          <p className="text-xs font-gilroy font-normal">Geen trends beschikbaar</p>
        ) : (
          <div className="flex flex-col justify-center space-y-0 min-h-[80px]">
            {trendsTr.items.slice(0, 10).map((item, index) => (
              <div
                key={item.id}
                className={cn(
                  "flex items-center gap-2 py-1.5",
                  index < trendsTr.items.length - 1 && "border-b border-border/40"
                )}
              >
                <span className="flex-shrink-0 text-[11px] font-gilroy font-semibold text-muted-foreground/70 leading-none">
                  {index + 1}.
                </span>
                <p className="line-clamp-1 text-[11px] font-gilroy font-medium leading-tight flex-1">
                  {item.title}
                </p>
              </div>
            ))}
          </div>
        )}
      </DashboardCard>
    </div>
  );
}









