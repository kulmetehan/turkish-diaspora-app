import * as DialogPrimitive from "@radix-ui/react-dialog";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import type { LocationMarker } from "@/api/fetchLocations";
import { LoginPrompt } from "@/components/auth/LoginPrompt";
import { Icon } from "@/components/Icon";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ClaimDialog } from "@/components/claim/ClaimDialog";
import { useViewportContext } from "@/contexts/viewport";
import { useUserAuth } from "@/hooks/useUserAuth";
import {
    addFavorite,
    createCheckIn,
    deleteNote,
    getCheckInStats,
    getLocationReactions,
    getNotes,
    isFavorite,
    removeFavorite,
    toggleLocationReaction,
    getClaimStatus,
    type CheckInStats,
    type NoteResponse,
    type ReactionStats,
    type ReactionType,
    type ClaimStatusResponse,
} from "@/lib/api";
import { cn } from "@/lib/ui/cn";
import { buildGoogleSearchUrl, buildRouteUrl, deriveCityForLocation } from "@/lib/urlBuilders";
import { toast } from "sonner";

type OverlayDetailCardProps = {
    location: LocationMarker;
    open: boolean;
    onClose: () => void;
    onAddNote?: () => void;
    onEditNote?: (note: NoteResponse) => void;
    onNotesRefresh?: () => void;
};

// Reaction type to emoji mapping
const REACTION_EMOJIS: Record<ReactionType, string> = {
    fire: "🔥",
    heart: "❤️",
    thumbs_up: "👍",
    smile: "😊",
    star: "⭐",
    flag: "🚩",
};

const REACTION_LABELS: Record<ReactionType, string> = {
    fire: "Fire",
    heart: "Heart",
    thumbs_up: "Thumbs Up",
    smile: "Smile",
    star: "Star",
    flag: "Flag",
};

function safeString(value: unknown): string | null {
    if (typeof value !== "string") return null;
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
}

export default function OverlayDetailCard({ location, open, onClose, onAddNote, onEditNote, onNotesRefresh }: OverlayDetailCardProps) {
    const { viewport } = useViewportContext();
    const { isAuthenticated } = useUserAuth();
    const navigate = useNavigate();
    const locationId = parseInt(location.id);
    const city = useMemo(() => deriveCityForLocation(location, "Unknown"), [location]);

    const routeUrl = useMemo(() => buildRouteUrl(location), [location]);
    const googleSearchUrl = useMemo(
        () =>
            buildGoogleSearchUrl(location.name, location.city, {
                loc: location,
                viewport,
            }),
        [location, viewport]
    );

    const routeLinkProps = useMemo(() => {
        const isWebTarget = routeUrl.startsWith("http");
        return {
            target: isWebTarget ? "_blank" : undefined,
            rel: isWebTarget ? "noopener noreferrer" : undefined,
        } as const;
    }, [routeUrl]);

    const googleLinkProps = useMemo(
        () => ({
            target: "_blank" as const,
            rel: "noopener noreferrer" as const,
        }),
        []
    );

    const categoryLabel = safeString(location.category_label) ?? safeString(location.category) ?? null;
    const address = safeString(location.address);

    const confidenceDisplay =
        typeof location.confidence_score === "number"
            ? `${Math.round(location.confidence_score * 100)}%`
            : null;

    // State for check-ins
    const [checkInStats, setCheckInStats] = useState<CheckInStats | null>(null);
    const [hasCheckedInToday, setHasCheckedInToday] = useState(false);
    const [isCheckingIn, setIsCheckingIn] = useState(false);

    // State for reactions
    const [reactionStats, setReactionStats] = useState<ReactionStats | null>(null);
    const [userReactions, setUserReactions] = useState<Set<ReactionType>>(new Set());
    const [reactionLoading, setReactionLoading] = useState<ReactionType | null>(null);

    // State for notes
    const [notes, setNotes] = useState<NoteResponse[]>([]);
    const [notesLoading, setNotesLoading] = useState(false);
    const [noteDeleting, setNoteDeleting] = useState<number | null>(null);

    // State for favorites
    const [isFavorited, setIsFavorited] = useState(false);
    const [favoriteLoading, setFavoriteLoading] = useState(false);

    // State for loading initial data
    const [initialLoading, setInitialLoading] = useState(true);

    // State for claim
    const [claimStatus, setClaimStatus] = useState<ClaimStatusResponse | null>(null);
    const [isClaimDialogOpen, setIsClaimDialogOpen] = useState(false);

    // Load initial data when dialog opens
    useEffect(() => {
        if (!open) return;

        const loadData = async () => {
            setInitialLoading(true);
            try {
                // Load check-in stats
                const checkInData = await getCheckInStats(locationId);
                setCheckInStats(checkInData);
                setHasCheckedInToday(checkInData.check_ins_today > 0);

                // Load reaction stats
                const reactionData = await getLocationReactions(locationId);
                setReactionStats({
                    location_id: locationId,
                    reactions: reactionData.reactions,
                });
                // Set user reaction from API response
                if (reactionData.user_reaction) {
                    setUserReactions(new Set([reactionData.user_reaction]));
                }

                // Load notes
                const notesData = await getNotes(locationId);
                setNotes(notesData);

                // Check favorite status
                const favorited = await isFavorite(locationId);
                setIsFavorited(favorited);

                // Load claim status (only if authenticated)
                if (isAuthenticated) {
                    try {
                        const claimData = await getClaimStatus(locationId);
                        setClaimStatus(claimData);
                    } catch (error: any) {
                        // Silently fail - claim status is optional
                        console.error("Failed to load claim status:", error);
                    }
                }
            } catch (error: any) {
                console.error("Failed to load location data:", error);
                // Don't show toast here to avoid spam when feature flags are off
            } finally {
                setInitialLoading(false);
            }
        };

        loadData();
    }, [locationId, open, isAuthenticated]);


    // Check-in handler
    const handleCheckIn = async () => {
        if (!isAuthenticated) {
            return; // LoginPrompt will be shown instead
        }
        if (hasCheckedInToday || isCheckingIn) return;

        setIsCheckingIn(true);
        try {
            await createCheckIn(locationId);
            toast.success("Check-in succesvol!");
            const stats = await getCheckInStats(locationId);
            setCheckInStats(stats);
            setHasCheckedInToday(true);
        } catch (error: any) {
            if (error.message?.includes("409") || error.message?.includes("already exists")) {
                toast.error("Je hebt vandaag al ingecheckt bij deze locatie");
                setHasCheckedInToday(true);
            } else {
                toast.error(error.message || "Fout bij check-in");
            }
        } finally {
            setIsCheckingIn(false);
        }
    };

    // Reaction handler
    const handleReaction = async (reactionType: ReactionType) => {
        if (reactionLoading) return;

        const hasReaction = userReactions.has(reactionType);
        setReactionLoading(reactionType);

        try {
            // Toggle reaction (add if not exists, remove if exists)
            const result = await toggleLocationReaction(locationId, reactionType);

            // Update user reactions based on result
            if (result.is_active) {
                // Remove old reaction if exists
                setUserReactions((prev) => {
                    const next = new Set(prev);
                    prev.forEach((rt) => next.delete(rt));
                    next.add(reactionType);
                    return next;
                });
            } else {
                // Remove reaction
                setUserReactions((prev) => {
                    const next = new Set(prev);
                    next.delete(reactionType);
                    return next;
                });
            }

            // Refresh stats
            const stats = await getLocationReactions(locationId);
            setReactionStats({
                location_id: locationId,
                reactions: stats.reactions,
            });
            if (stats.user_reaction) {
                setUserReactions(new Set([stats.user_reaction]));
            } else {
                setUserReactions(new Set());
            }
        } catch (error: any) {
            toast.error(error.message || "Fout bij bijwerken van reaction");
        } finally {
            setReactionLoading(null);
        }
    };

    // Note handlers - delegate to parent component
    const handleAddNote = () => {
        if (!isAuthenticated) {
            return; // LoginPrompt will be shown instead
        }
        onAddNote?.();
    };

    const handleEditNote = (note: NoteResponse) => {
        if (!isAuthenticated) {
            return; // LoginPrompt will be shown instead
        }
        onEditNote?.(note);
    };

    const handleDeleteNote = async (noteId: number) => {
        if (!confirm("Weet je zeker dat je deze notitie wilt verwijderen?")) {
            return;
        }

        setNoteDeleting(noteId);
        try {
            await deleteNote(noteId);
            toast.success("Notitie verwijderd");
            const notesData = await getNotes(locationId);
            setNotes(notesData);
            onNotesRefresh?.();
        } catch (error: any) {
            toast.error(error.message || "Fout bij verwijderen van notitie");
        } finally {
            setNoteDeleting(null);
        }
    };

    // Favorite handler
    const handleToggleFavorite = async () => {
        if (favoriteLoading) return;

        setFavoriteLoading(true);
        try {
            if (isFavorited) {
                await removeFavorite(locationId);
                setIsFavorited(false);
                toast.success("Verwijderd uit favorieten");
            } else {
                await addFavorite(locationId);
                setIsFavorited(true);
                toast.success("Toegevoegd aan favorieten");
            }
        } catch (error: any) {
            if (error.message?.includes("409") || error.message?.includes("already")) {
                setIsFavorited(true);
                toast.info("Locatie staat al in je favorieten");
            } else {
                toast.error(error.message || "Fout bij bijwerken van favorieten");
            }
        } finally {
            setFavoriteLoading(false);
        }
    };

    // Calculate total reactions count
    const totalReactions = reactionStats
        ? Object.values(reactionStats.reactions).reduce((sum, count) => sum + count, 0)
        : 0;

    return (
        <>
            <DialogPrimitive.Root open={open} onOpenChange={(next) => { if (!next) onClose(); }}>
                <DialogPrimitive.Portal>
                    <DialogPrimitive.Overlay
                        className={cn(
                            "fixed inset-0 z-[55] bg-black/40 backdrop-blur",
                            "pointer-events-none data-[state=open]:pointer-events-auto",
                            "data-[state=closed]:animate-out data-[state=closed]:fade-out-0",
                            "data-[state=open]:animate-in data-[state=open]:fade-in-0",
                        )}
                    />
                    <DialogPrimitive.Content
                        className={cn(
                            "fixed inset-x-0 bottom-0 top-auto z-[60] mx-auto w-full max-w-screen-sm",
                            "flex max-h-[min(70vh,560px)] flex-col rounded-t-[40px] border border-white/15 bg-surface-raised/95 text-foreground shadow-[0_-40px_80px_rgba(0,0,0,0.6)] backdrop-blur-2xl",
                            "px-5 pt-6 pb-[calc(env(safe-area-inset-bottom)+20px)]",
                            "focus:outline-none data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:slide-in-from-bottom",
                            "data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:slide-out-to-bottom",
                            "lg:left-1/2 lg:right-auto lg:top-1/2 lg:bottom-auto lg:max-h-[85vh] lg:w-[min(90vw,840px)] lg:max-w-[min(90vw,840px)] lg:-translate-x-1/2 lg:-translate-y-1/2",
                            "lg:rounded-[40px] lg:px-6 lg:pb-6 lg:shadow-[0_45px_90px_rgba(0,0,0,0.6)]",
                            "lg:data-[state=open]:zoom-in-95 lg:data-[state=closed]:zoom-out-95",
                        )}
                        aria-labelledby="overlay-detail-title"
                        aria-describedby="overlay-detail-description"
                    >
                        <header className="flex flex-col gap-4 border-b border-white/10 pb-4 lg:flex-row lg:items-start lg:justify-between">
                            <div className="min-w-0 flex-1 space-y-3">
                                <div>
                                    <DialogPrimitive.Title
                                        id="overlay-detail-title"
                                        className="truncate text-2xl font-semibold tracking-tight"
                                    >
                                        {location.name}
                                    </DialogPrimitive.Title>
                                    <div className="h-[3px] w-12 rounded-full bg-brand-white/50 mt-2" />
                                </div>
                                <div className="flex flex-wrap items-center gap-2">
                                    {categoryLabel && (
                                        <Badge variant="secondary" className="capitalize">
                                            {categoryLabel}
                                        </Badge>
                                    )}
                                    {confidenceDisplay && (
                                        <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                                            <Icon name="Target" className="h-3.5 w-3.5" />
                                            {confidenceDisplay} confidence
                                        </span>
                                    )}
                                </div>
                            </div>
                            <div className="flex items-center gap-2 self-end lg:self-auto">
                                <Button
                                    asChild
                                    variant="outline"
                                    size="icon"
                                    aria-label="Open route in Maps"
                                    title="Open route in Maps"
                                    className="border-white/20 text-foreground hover:bg-white/10"
                                >
                                    <a href={routeUrl} {...routeLinkProps}>
                                        <Icon name="Navigation" className="h-4 w-4" />
                                    </a>
                                </Button>
                                <Button
                                    asChild
                                    variant="outline"
                                    size="icon"
                                    aria-label="Search on Google"
                                    title="Search on Google"
                                    className="border-white/20 text-foreground hover:bg-white/10"
                                >
                                    <a href={googleSearchUrl} {...googleLinkProps}>
                                        <Icon name="Search" className="h-4 w-4" />
                                    </a>
                                </Button>
                                <Button
                                    variant="outline"
                                    size="icon"
                                    aria-label="Claim deze locatie"
                                    title="Claim deze locatie"
                                    onClick={() => {
                                        if (!isAuthenticated) {
                                            navigate("/auth");
                                        } else if (claimStatus?.can_claim) {
                                            setIsClaimDialogOpen(true);
                                        }
                                    }}
                                    className="border-white/20 text-foreground hover:bg-white/10"
                                >
                                    <Icon name="ShieldCheck" className="h-4 w-4" />
                                </Button>
                                <DialogPrimitive.Close
                                    className="ml-1 rounded-full border border-white/10 p-2 text-brand-white/70 transition hover:border-white/30 hover:text-brand-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-white/70"
                                    aria-label="Close details"
                                >
                                    <Icon name="X" className="h-4 w-4" />
                                </DialogPrimitive.Close>
                            </div>
                        </header>

                        <div
                            id="overlay-detail-description"
                            className="mt-4 flex-1 overflow-y-auto"
                        >
                            <div className="space-y-5">
                                {address && (
                                    <Card className="p-4">
                                        <div className="flex items-start gap-3">
                                            <Icon name="MapPin" className="mt-0.5 h-4 w-4 text-foreground/70" />
                                            <div>
                                                <p className="text-sm font-medium text-foreground/70">Address</p>
                                                <p className="mt-1 text-sm leading-snug">{address}</p>
                                            </div>
                                        </div>
                                    </Card>
                                )}

                                <Card className="p-4">
                                    <div className="space-y-3 text-sm text-foreground/70">
                                        <div className="flex items-center gap-3">
                                            <Icon name="Tags" className="h-4 w-4" />
                                            <span>
                                                Category:{" "}
                                                <span className="font-medium text-foreground">
                                                    {categoryLabel ?? "Unknown"}
                                                </span>
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-3">
                                            <Icon name="Map" className="h-4 w-4" />
                                            <span>
                                                City: <span className="font-medium text-foreground">{city}</span>
                                            </span>
                                        </div>
                                        {location.state && (
                                            <div className="flex items-center gap-3">
                                                <Icon name="Shield" className="h-4 w-4" />
                                                <span>
                                                    Verification state:{" "}
                                                    <span className="font-medium text-foreground capitalize">
                                                        {location.state.toLowerCase()}
                                                    </span>
                                                </span>
                                            </div>
                                        )}
                                    </div>
                                </Card>

                                {initialLoading ? (
                                    <Card className="p-4">
                                        <div className="text-center text-sm text-foreground/70">Laden...</div>
                                    </Card>
                                ) : (
                                    <>
                                        {/* Interaction Actions Bar */}
                                        <Card className="p-4">
                                            {!isAuthenticated ? (
                                                <LoginPrompt message="Log in om in te checken" className="mb-0" />
                                            ) : (
                                                <div className="flex items-center gap-2 flex-wrap">
                                                    <Button
                                                        onClick={handleCheckIn}
                                                        disabled={hasCheckedInToday || isCheckingIn}
                                                        variant={hasCheckedInToday ? "secondary" : "default"}
                                                        size="sm"
                                                        className="border-white/20 text-brand-white hover:bg-white/10"
                                                    >
                                                        {isCheckingIn ? (
                                                            "Check-in..."
                                                        ) : hasCheckedInToday ? (
                                                            <>
                                                                <Icon name="CheckCircle" className="h-4 w-4 mr-2" />
                                                                Ingecheckt
                                                            </>
                                                        ) : (
                                                            <>
                                                                <Icon name="MapPin" className="h-4 w-4 mr-2" />
                                                                Check-in
                                                            </>
                                                        )}
                                                    </Button>

                                                    <Button
                                                        onClick={handleToggleFavorite}
                                                        disabled={favoriteLoading}
                                                        variant={isFavorited ? "default" : "outline"}
                                                        size="sm"
                                                        className="border-white/20 text-foreground hover:bg-white/10"
                                                    >
                                                        <Icon name="Star" className={`h-4 w-4 mr-2 ${isFavorited ? "fill-current" : ""}`} />
                                                        {favoriteLoading ? "..." : isFavorited ? "Favoriet" : "Favoriet"}
                                                    </Button>
                                                </div>
                                            )}
                                        </Card>

                                        {/* Stats Overview Card */}
                                        <Card className="p-4">
                                            <h3 className="font-medium text-sm mb-3 text-foreground">Interacties</h3>
                                            <div className="grid grid-cols-3 gap-4 text-center">
                                                <div>
                                                    <div className="text-2xl font-bold text-foreground">
                                                        {checkInStats?.total_check_ins ?? 0}
                                                    </div>
                                                    <div className="text-xs text-foreground/70">Check-ins</div>
                                                </div>
                                                <div>
                                                    <div className="text-2xl font-bold text-foreground">{totalReactions}</div>
                                                    <div className="text-xs text-foreground/70">Reactions</div>
                                                </div>
                                                <div>
                                                    <div className="text-2xl font-bold text-foreground">{notes.length}</div>
                                                    <div className="text-xs text-foreground/70">Notities</div>
                                                </div>
                                            </div>
                                        </Card>

                                        {/* Check-in Stats Card */}
                                        {checkInStats && (
                                            <Card className="p-4">
                                                <div className="flex items-center justify-between mb-2">
                                                    <h3 className="font-medium text-sm text-foreground">Check-ins</h3>
                                                    <Badge variant="secondary">{checkInStats.total_check_ins} totaal</Badge>
                                                </div>
                                                <div className="text-sm text-foreground/70">
                                                    {checkInStats.check_ins_today} vandaag • {checkInStats.unique_users_today} gebruikers
                                                </div>
                                            </Card>
                                        )}

                                        {/* Reactions Section */}
                                        <Card className="p-4">
                                            <h3 className="font-medium text-sm mb-3 text-foreground">Reactions</h3>
                                            <div className="flex flex-wrap gap-2">
                                                {(Object.keys(REACTION_EMOJIS) as ReactionType[]).map((reactionType) => {
                                                    const count = reactionStats?.reactions[reactionType] ?? 0;
                                                    const isActive = userReactions.has(reactionType);
                                                    const isLoading = reactionLoading === reactionType;

                                                    return (
                                                        <Button
                                                            key={reactionType}
                                                            onClick={() => handleReaction(reactionType)}
                                                            disabled={isLoading}
                                                            variant={isActive ? "default" : "outline"}
                                                            size="sm"
                                                            className="relative border-white/20 text-brand-white hover:bg-white/10"
                                                        >
                                                            <span className="text-lg mr-1">{REACTION_EMOJIS[reactionType]}</span>
                                                            <span className="text-xs">{REACTION_LABELS[reactionType]}</span>
                                                            {count > 0 && (
                                                                <Badge
                                                                    variant="secondary"
                                                                    className="ml-2 h-5 min-w-5 px-1.5 text-xs bg-transparent"
                                                                >
                                                                    {count}
                                                                </Badge>
                                                            )}
                                                        </Button>
                                                    );
                                                })}
                                            </div>
                                        </Card>

                                        {/* Notes Section */}
                                        <Card className="p-4">
                                            <div className="flex items-center justify-between mb-3">
                                                <h3 className="font-medium text-sm text-foreground">Notities</h3>
                                                {isAuthenticated ? (
                                                    <Button onClick={handleAddNote} size="sm" variant="outline" className="border-white/30 bg-white/10 text-foreground hover:bg-white/20 hover:border-white/40">
                                                        <Icon name="Plus" className="h-4 w-4 mr-2" />
                                                        Notitie toevoegen
                                                    </Button>
                                                ) : null}
                                            </div>
                                            {!isAuthenticated && (
                                                <LoginPrompt message="Log in om een notitie toe te voegen" className="mb-3" />
                                            )}

                                            {notesLoading ? (
                                                <div className="text-center text-sm text-foreground/70 py-4">Laden...</div>
                                            ) : notes.length === 0 ? (
                                                <div className="text-center text-sm text-foreground/70 py-4">
                                                    Nog geen notities. Voeg de eerste toe!
                                                </div>
                                            ) : (
                                                <div className="space-y-3">
                                                    {notes.map((note) => (
                                                        <div
                                                            key={note.id}
                                                            className="border rounded-lg p-3 space-y-2 bg-muted/30"
                                                        >
                                                            <div className="text-sm whitespace-pre-wrap text-foreground">{note.content}</div>
                                                            <div className="flex items-center justify-between text-xs text-foreground/70">
                                                                <span>
                                                                    {new Date(note.created_at).toLocaleDateString("nl-NL", {
                                                                        day: "numeric",
                                                                        month: "short",
                                                                        year: "numeric",
                                                                        hour: "2-digit",
                                                                        minute: "2-digit",
                                                                    })}
                                                                    {note.is_edited && " (bewerkt)"}
                                                                </span>
                                                                <div className="flex gap-2">
                                                                    <Button
                                                                        onClick={() => handleEditNote(note)}
                                                                        size="sm"
                                                                        variant="ghost"
                                                                        className="h-6 px-2 text-xs text-foreground hover:bg-white/10"
                                                                    >
                                                                        Bewerken
                                                                    </Button>
                                                                    <Button
                                                                        onClick={() => handleDeleteNote(note.id)}
                                                                        size="sm"
                                                                        variant="ghost"
                                                                        className="h-6 px-2 text-xs text-destructive hover:bg-white/10"
                                                                        disabled={noteDeleting === note.id}
                                                                    >
                                                                        {noteDeleting === note.id ? "Verwijderen..." : "Verwijderen"}
                                                                    </Button>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </Card>
                                    </>
                                )}
                            </div>
                        </div>
                    </DialogPrimitive.Content>
                </DialogPrimitive.Portal>
                <ClaimDialog
                    location={location}
                    open={isClaimDialogOpen}
                    onClose={() => setIsClaimDialogOpen(false)}
                    onSuccess={async () => {
                        // Refresh claim status after successful submission
                        if (isAuthenticated) {
                            try {
                                const claimData = await getClaimStatus(locationId);
                                setClaimStatus(claimData);
                            } catch (error: any) {
                                console.error("Failed to refresh claim status:", error);
                            }
                        }
                    }}
                />
            </DialogPrimitive.Root>

        </>
    );
}
