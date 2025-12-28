// Frontend/src/components/prikbord/PrikbordFeed.tsx
import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { ReactionType } from "@/lib/api";
import { getSharedLinks, toggleSharedLinkReaction } from "@/lib/api/prikbord";
import { cn } from "@/lib/ui/cn";
import type { SharedLink, SharedLinkFilters } from "@/types/prikbord";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { PrikbordFilters } from "./PrikbordFilters";
import { SharedLinkCard } from "./SharedLinkCard";
import { ShareLinkDialog } from "./ShareLinkDialog";

interface PrikbordFeedProps {
    className?: string;
    initialFilters?: SharedLinkFilters;
    onLinkClick?: (link: SharedLink) => void;
}

const INITIAL_LIMIT = 20;
const LOAD_MORE_LIMIT = 20;

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
    const [filters, setFilters] = useState<SharedLinkFilters>(
        initialFilters || {}
    );
    const [isShareDialogOpen, setIsShareDialogOpen] = useState(false);

    const loadInitialData = useCallback(async () => {
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

    useEffect(() => {
        // Reset and reload when filters change
        setOffset(0);
        setHasMore(true);
        loadInitialData();
    }, [loadInitialData]);

    const handleShareSuccess = () => {
        // Refresh feed
        setOffset(0);
        setHasMore(true);
        loadInitialData();
    };

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
                <div className="flex items-center justify-between gap-4">
                    <PrikbordFilters filters={filters} onFiltersChange={setFilters} />
                    <Button
                        onClick={() => setIsShareDialogOpen(true)}
                        size="sm"
                        className="gap-2 shrink-0"
                    >
                        <Icon name="Plus" className="h-4 w-4" />
                        Deel link
                    </Button>
                </div>
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
                <div className="flex items-center justify-between gap-4">
                    <PrikbordFilters filters={filters} onFiltersChange={setFilters} />
                    <Button
                        onClick={() => setIsShareDialogOpen(true)}
                        size="sm"
                        className="gap-2 shrink-0"
                    >
                        <Icon name="Plus" className="h-4 w-4" />
                        Deel link
                    </Button>
                </div>
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
            <div className="flex items-center justify-between gap-4">
                <PrikbordFilters filters={filters} onFiltersChange={setFilters} />
                <Button
                    onClick={() => setIsShareDialogOpen(true)}
                    size="sm"
                    className="gap-2 shrink-0"
                >
                    <Icon name="Plus" className="h-4 w-4" />
                    Deel link
                </Button>
            </div>

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

            <ShareLinkDialog
                open={isShareDialogOpen}
                onOpenChange={setIsShareDialogOpen}
                onSuccess={handleShareSuccess}
            />
        </div>
    );
}

