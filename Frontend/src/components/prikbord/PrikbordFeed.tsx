// Frontend/src/components/prikbord/PrikbordFeed.tsx
import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { ReactionType } from "@/lib/api";
import { getSharedLinks, toggleSharedLinkReaction, deleteSharedLink } from "@/lib/api/prikbord";
import { cn } from "@/lib/ui/cn";
import type { SharedLink, SharedLinkFilters } from "@/types/prikbord";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { SharedLinkCard } from "./SharedLinkCard";
import { PrikbordComposer } from "./PrikbordComposer";

interface PrikbordFeedProps {
    className?: string;
    initialFilters?: SharedLinkFilters;
    onLinkClick?: (link: SharedLink) => void;
}

const INITIAL_LIMIT = 20;
const LOAD_MORE_LIMIT = 20;

// Stable empty filters object to prevent infinite loops
const EMPTY_FILTERS: SharedLinkFilters = {};

export function PrikbordFeed({
    className,
    initialFilters,
    onLinkClick,
}: PrikbordFeedProps) {
    const [links, setLinks] = useState<SharedLink[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isLoadingMore, setIsLoadingMore] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [hasMore, setHasMore] = useState(true);
    const [offset, setOffset] = useState(0);
    const isLoadingRef = useRef(false);
    
    // Memoize filters to prevent infinite loops - use stable empty object as default
    const filters = useMemo(() => {
        if (!initialFilters) return EMPTY_FILTERS;
        return initialFilters;
    }, [
        initialFilters?.platform,
        initialFilters?.city,
        initialFilters?.tags?.join(','),
        initialFilters?.post_type,
        initialFilters?.trending,
        initialFilters?.search,
    ]);

    const loadInitialData = useCallback(async () => {
        if (isLoadingRef.current) return; // Prevent concurrent loads
        isLoadingRef.current = true;
        setIsLoading(true);
        setError(null);
        try {
            const data = await getSharedLinks(filters, INITIAL_LIMIT, 0);
            setLinks(data);
            setOffset(data.length);
            setHasMore(data.length >= INITIAL_LIMIT);
        } catch (err) {
            const message =
                err instanceof Error ? err.message : "Kon links niet laden";
            setError(message);
            toast.error(message);
        } finally {
            setIsLoading(false);
            isLoadingRef.current = false;
        }
    }, [filters]);

    const loadMore = useCallback(async () => {
        if (isLoadingMore || !hasMore) return;

        setIsLoadingMore(true);
        try {
            const data = await getSharedLinks(filters, LOAD_MORE_LIMIT, offset);
            if (data.length > 0) {
                setLinks((prev) => [...prev, ...data]);
                setOffset((prev) => prev + data.length);
                setHasMore(data.length >= LOAD_MORE_LIMIT);
            } else {
                setHasMore(false);
            }
        } catch (err) {
            const message =
                err instanceof Error ? err.message : "Kon meer links niet laden";
            toast.error(message);
        } finally {
            setIsLoadingMore(false);
        }
    }, [isLoadingMore, hasMore, offset, filters]);

    // Serialize filters for stable comparison
    const filtersKey = useMemo(() => {
        return JSON.stringify({
            platform: filters.platform,
            city: filters.city,
            tags: filters.tags?.sort().join(','),
            post_type: filters.post_type,
            trending: filters.trending,
            search: filters.search,
        });
    }, [
        filters.platform,
        filters.city,
        filters.tags?.join(','),
        filters.post_type,
        filters.trending,
        filters.search,
    ]);

    useEffect(() => {
        // Reset and reload when filters change
        if (isLoadingRef.current) return; // Prevent concurrent loads
        setOffset(0);
        setHasMore(true);
        loadInitialData();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [filtersKey]);

    const handlePostSuccess = useCallback((newPost?: SharedLink) => {
        // Optimistic update: add new post to beginning of list
        if (newPost) {
            setLinks((prev) => [newPost, ...prev]);
            // Update offset to account for new post
            setOffset((prev) => prev + 1);
        } else {
            // Fallback: refresh feed if no post provided
            setOffset(0);
            setHasMore(true);
            loadInitialData();
        }
    }, [loadInitialData]);

    const handleDelete = useCallback(async (linkId: number) => {
        try {
            // Optimistic delete: remove post from list immediately
            setLinks((prev) => prev.filter((link) => link.id !== linkId));
            setOffset((prev) => Math.max(0, prev - 1));
            
            // Call API to delete
            await deleteSharedLink(linkId);
            toast.success("Post verwijderd");
        } catch (err: any) {
            // Rollback on error: reload feed
            toast.error("Kon post niet verwijderen", {
                description: err.message || "Er is een fout opgetreden",
            });
            // Reload feed to sync state
            loadInitialData();
        }
    }, [loadInitialData]);

    const handleReactionToggle = useCallback(async (linkId: number, reactionType: ReactionType) => {
        try {
            const result = await toggleSharedLinkReaction(linkId, reactionType);

            // Update the link in state
            setLinks((prev) =>
                prev.map((link) => {
                    if (link.id === linkId) {
                        const currentReactions = link.reactions || {};
                        const newReactions = { ...currentReactions };

                        if (result.is_active) {
                            // Add reaction
                            newReactions[reactionType] = result.count;
                            return {
                                ...link,
                                reactions: newReactions,
                                user_reaction: reactionType,
                            };
                        } else {
                            // Remove reaction
                            if (newReactions[reactionType]) {
                                newReactions[reactionType] = result.count;
                                if (newReactions[reactionType] === 0) {
                                    delete newReactions[reactionType];
                                }
                            }
                            return {
                                ...link,
                                reactions: Object.keys(newReactions).length > 0 ? newReactions : null,
                                user_reaction: link.user_reaction === reactionType ? null : link.user_reaction,
                            };
                        }
                    }
                    return link;
                })
            );
        } catch (err: any) {
            toast.error("Kon reactie niet updaten", {
                description: err.message || "Er is een fout opgetreden",
            });
        }
    }, []);

    if (isLoading) {
        return (
            <div className={cn("space-y-4", className)}>
                <div className="space-y-4">
                    {Array.from({ length: 3 }).map((_, i) => (
                        <Skeleton key={i} className="h-64 w-full rounded-xl" />
                    ))}
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className={cn("space-y-4", className)}>
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
            <PrikbordComposer onSuccess={handlePostSuccess} />

            {links.length === 0 ? (
                <div className="text-center py-12">
                    <p className="text-muted-foreground mb-4">
                        Nog geen links gedeeld. Deel de eerste link!
                    </p>
                </div>
            ) : (
                <>
                    <div className="space-y-4">
                        {links.map((link) => (
                            <SharedLinkCard
                                key={link.id}
                                link={link}
                                onDetailClick={() => onLinkClick?.(link)}
                                onReactionToggle={(reactionType) => handleReactionToggle(link.id, reactionType)}
                                onDelete={() => handleDelete(link.id)}
                                reactions={link.reactions || null}
                                userReaction={(link.user_reaction as ReactionType) || null}
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

