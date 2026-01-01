// Frontend/src/components/feed/FeedList.tsx
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/ui/cn";
import { FeedCard, type FeedCardProps } from "./FeedCard";
import { LoginPrompt } from "@/components/auth/LoginPrompt";
import { useTranslation } from "@/hooks/useTranslation";

export interface FeedListProps {
  items: FeedCardProps[];
  isLoading?: boolean;
  isLoadingMore?: boolean;
  hasMore?: boolean;
  onLoadMore?: () => void;
  emptyMessage?: string;
  className?: string;
  showLoginPrompt?: boolean;
  loginMessage?: string;
}

export function FeedList({
  items,
  isLoading = false,
  isLoadingMore = false,
  hasMore = false,
  onLoadMore,
  emptyMessage,
  className,
  showLoginPrompt = false,
  loginMessage,
}: FeedListProps) {
  const { t } = useTranslation();
  const defaultEmptyMessage = emptyMessage || t("feed.list.emptyMessage");
  if (isLoading) {
    return (
      <div className={cn("space-y-4", className)}>
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="rounded-xl border border-border/50 bg-card p-4 shadow-soft">
            <div className="flex items-start gap-3">
              <Skeleton className="h-10 w-10 rounded-full" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-3 w-1/2" />
                <Skeleton className="h-3 w-2/3" />
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    // Show login prompt if requested (when user is not authenticated)
    if (showLoginPrompt) {
      return (
        <div className={cn("", className)}>
          <LoginPrompt message={loginMessage || t("feed.list.loginToSeeActivity")} />
        </div>
      );
    }

    // Otherwise show empty state message
    return (
      <div className={cn(
        "rounded-xl border border-border/50 bg-card p-6 text-center text-muted-foreground shadow-soft",
        className
      )}>
        <p>{defaultEmptyMessage}</p>
      </div>
    );
  }

  return (
    <div className={cn("space-y-4", className)}>
      {items.map((item) => (
        <FeedCard key={item.id} {...item} />
      ))}
      {hasMore && (
        <div className="flex justify-center pt-2">
          {isLoadingMore ? (
            <p className="text-sm text-muted-foreground">{t("feed.list.loadingMore")}</p>
          ) : (
            onLoadMore && (
              <Button
                size="sm"
                variant="outline"
                onClick={onLoadMore}
                className="border-border text-foreground hover:bg-muted"
              >
                {t("feed.list.loadMore")}
              </Button>
            )
          )}
        </div>
      )}
    </div>
  );
}











