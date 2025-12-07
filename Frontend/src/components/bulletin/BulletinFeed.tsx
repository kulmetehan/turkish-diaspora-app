// Frontend/src/components/bulletin/BulletinFeed.tsx
import { useEffect, useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/ui/cn";
import { getBulletinPosts } from "@/lib/api/bulletin";
import type { BulletinPost, BulletinPostFilters } from "@/types/bulletin";
import { BulletinPostCard } from "./BulletinPostCard";
import { BulletinFilters } from "./BulletinFilters";
import { BulletinEmptyState } from "./BulletinEmptyState";
import { toast } from "sonner";

interface BulletinFeedProps {
  className?: string;
  onPostClick?: (post: BulletinPost) => void;
  initialFilters?: BulletinPostFilters;
}

const INITIAL_LIMIT = 20;
const LOAD_MORE_LIMIT = 20;

export function BulletinFeed({ className, onPostClick, initialFilters }: BulletinFeedProps) {
  const [posts, setPosts] = useState<BulletinPost[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [offset, setOffset] = useState(0);
  const [filters, setFilters] = useState<BulletinPostFilters>(
    initialFilters || { status: "active" }
  );

  const loadInitialData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getBulletinPosts(filters, INITIAL_LIMIT, 0);
      setPosts(data);
      setOffset(data.length);
      setHasMore(data.length >= INITIAL_LIMIT);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Kon advertenties niet laden";
      setError(message);
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  }, [filters]);

  const loadMore = useCallback(async () => {
    if (isLoadingMore || !hasMore) return;

    setIsLoadingMore(true);
    try {
      const data = await getBulletinPosts(filters, LOAD_MORE_LIMIT, offset);
      if (data.length > 0) {
        setPosts((prev) => [...prev, ...data]);
        setOffset((prev) => prev + data.length);
        setHasMore(data.length >= LOAD_MORE_LIMIT);
      } else {
        setHasMore(false);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Kon meer advertenties niet laden";
      toast.error(message);
    } finally {
      setIsLoadingMore(false);
    }
  }, [isLoadingMore, hasMore, offset, filters]);

  useEffect(() => {
    // Reset and reload when filters change
    setPosts([]);
    setOffset(0);
    setHasMore(true);
    loadInitialData();
  }, [loadInitialData]);

  if (isLoading) {
    return (
      <div className={cn("space-y-4", className)}>
        <BulletinFilters filters={filters} onFiltersChange={setFilters} />
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-48 w-full rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn("space-y-4", className)}>
        <BulletinFilters filters={filters} onFiltersChange={setFilters} />
        <div className="text-center py-8">
          <p className="text-destructive">{error}</p>
          <Button variant="outline" onClick={loadInitialData} className="mt-4">
            Opnieuw proberen
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("space-y-4", className)}>
      <BulletinFilters filters={filters} onFiltersChange={setFilters} />

      {posts.length === 0 ? (
        <BulletinEmptyState filters={filters} />
      ) : (
        <>
          <div className="space-y-4">
            {posts.map((post) => (
              <BulletinPostCard
                key={post.id}
                post={post}
                onDetailClick={() => onPostClick?.(post)}
              />
            ))}
          </div>

          {hasMore && (
            <Button
              variant="outline"
              className="w-full"
              onClick={loadMore}
              disabled={isLoadingMore}
            >
              {isLoadingMore ? "Laden..." : "Meer laden"}
            </Button>
          )}
        </>
      )}
    </div>
  );
}

