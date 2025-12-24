import * as DialogPrimitive from "@radix-ui/react-dialog";
import { useEffect, useMemo, useState } from "react";

import type { LocationMarker } from "@/api/fetchLocations";
import { LoginPrompt } from "@/components/auth/LoginPrompt";
import { Icon } from "@/components/Icon";
import NoteDialog from "@/components/location/NoteDialog";
import { ReportButton } from "@/components/report/ReportButton";
import { ShareButton } from "@/components/share/ShareButton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useViewportContext } from "@/contexts/viewport";
import { useUserAuth } from "@/hooks/useUserAuth";
import {
    addFavorite,
    createCheckIn,
    createNote,
    deleteNote,
    getCheckInStats,
    getLocationReactions,
    getNotes,
    isFavorite,
    removeFavorite,
    toggleLocationReaction,
    updateNote,
    type CheckInStats,
    type NoteResponse,
    type ReactionStats,
    type ReactionType,
} from "@/lib/api";
import { getCategoryIcon } from "@/lib/map/marker-icons";
import { cn } from "@/lib/ui/cn";
import { buildGoogleSearchUrl, buildRouteUrl, deriveCityForLocation } from "@/lib/urlBuilders";
import { toast } from "sonner";

type Props = {
    location: LocationMarker;
    viewMode: "list" | "map";
    onBack: () => void;
    open?: boolean; // Voor map view (Dialog)
    onClose?: () => void; // Voor map view
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

function safeString(value: unknown): string | null {
    if (typeof value !== "string") return null;
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
}

export default function UnifiedLocationDetail({
    location,
    viewMode,
    onBack,
    open,
    onClose,
    onAddNote,
    onEditNote,
    onNotesRefresh,
}: Props) {
    const { viewport } = useViewportContext();
    const { isAuthenticated } = useUserAuth();
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
    const categoryKey = location.category_key ?? location.category ?? null;
    const CategoryIcon = categoryKey ? getCategoryIcon(categoryKey) : null;
    const address = safeString(location.address);

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
    const [isNoteDialogOpen, setIsNoteDialogOpen] = useState(false);
    const [editingNote, setEditingNote] = useState<NoteResponse | null>(null);
    const [notesLoading, setNotesLoading] = useState(false);
    const [noteDeleting, setNoteDeleting] = useState<number | null>(null);

    // State for favorites
    const [isFavorited, setIsFavorited] = useState(false);
    const [favoriteLoading, setFavoriteLoading] = useState(false);

    // State for loading initial data
    const [initialLoading, setInitialLoading] = useState(true);

    // Load initial data
    useEffect(() => {
        // For map view, only load when open
        if (viewMode === "map" && !open) return;

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
            } catch (error: any) {
                console.error("Failed to load location data:", error);
                if (viewMode === "list") {
                    toast.error("Fout bij laden van locatie data");
                }
            } finally {
                setInitialLoading(false);
            }
        };

        loadData();
    }, [locationId, viewMode, open]);

    // Check-in handler
    const handleCheckIn = async () => {
        if (hasCheckedInToday || isCheckingIn) return;

        setIsCheckingIn(true);
        try {
            await createCheckIn(locationId);
            toast.success("Check-in succesvol!");
            // Refresh stats
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

    // Note handlers
    const handleAddNote = () => {
        if (!isAuthenticated) {
            return; // LoginPrompt will be shown instead
        }
        if (viewMode === "map" && onAddNote) {
            onAddNote();
        } else {
            setEditingNote(null);
            setIsNoteDialogOpen(true);
        }
    };

    const handleEditNote = (note: NoteResponse) => {
        if (!isAuthenticated) {
            return; // LoginPrompt will be shown instead
        }
        if (viewMode === "map" && onEditNote) {
            onEditNote(note);
        } else {
            setEditingNote(note);
            setIsNoteDialogOpen(true);
        }
    };

    const handleSaveNote = async (content: string) => {
        try {
            if (editingNote) {
                // Optimistic update for edit
                setNotes((prevNotes) =>
                    prevNotes.map((note) =>
                        note.id === editingNote.id
                            ? { ...note, content, is_edited: true, updated_at: new Date().toISOString() }
                            : note
                    )
                );
                await updateNote(editingNote.id, content);
                toast.success("Notitie bijgewerkt");
            } else {
                // Optimistic update for create - add temporary note
                const tempNote: NoteResponse = {
                    id: Date.now(), // Temporary ID
                    location_id: locationId,
                    content,
                    is_edited: false,
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                };
                setNotes((prevNotes) => [tempNote, ...prevNotes]);

                const newNote = await createNote(locationId, content);
                // Replace temporary note with real one from server
                setNotes((prevNotes) =>
                    prevNotes.map((note) => (note.id === tempNote.id ? newNote : note))
                );
                toast.success("Notitie toegevoegd");
            }

            setIsNoteDialogOpen(false);
            setEditingNote(null);
            if (onNotesRefresh) {
                onNotesRefresh();
            }
        } catch (error: any) {
            // Rollback optimistic update on error
            const notesData = await getNotes(locationId);
            setNotes(notesData);
            throw error; // Let NoteDialog handle the error
        }
    };

    const handleDeleteNote = async (noteId: number) => {
        if (!confirm("Weet je zeker dat je deze notitie wilt verwijderen?")) {
            return;
        }

        setNoteDeleting(noteId);
        try {
            await deleteNote(noteId);
            toast.success("Notitie verwijderd");
            // Refresh notes
            const notesData = await getNotes(locationId);
            setNotes(notesData);
            if (onNotesRefresh) {
                onNotesRefresh();
            }
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

    const backButtonText = viewMode === "list" ? "Back to List" : "Terug naar kaart";

    // Content for map view (with white Card container)
    const mapViewContent = (
        <Card className="border border-white/10 bg-white/95 backdrop-blur-sm">
            <div className="p-4 space-y-4">
                {/* Back and Report buttons - highest items */}
                <div className="flex items-center justify-between">
                    <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            onBack();
                        }}
                        className="flex items-center gap-2 text-foreground dark:text-gray-900 hover:text-primary hover:bg-transparent transition-colors font-gilroy"
                    >
                        <Icon name="ArrowUp" className="h-4 w-4" />
                        {backButtonText}
                    </Button>
                    <ReportButton
                        reportType="location"
                        targetId={locationId}
                        targetName={location.name}
                        size="sm"
                        variant="ghost"
                        className="text-foreground dark:text-gray-900 hover:text-primary hover:bg-transparent transition-colors font-gilroy"
                    />
                </div>

                {/* Title */}
                <h2 className="text-base font-gilroy font-semibold text-foreground dark:text-gray-900">{location.name}</h2>

                {/* Category, Favorite, Share on same row */}
                <div className="flex items-center gap-2 flex-wrap">
                    {categoryLabel && CategoryIcon && (
                        <div className="flex items-center gap-2 border border-brand-red text-brand-red px-2 py-1 rounded w-fit">
                            <CategoryIcon className="h-3.5 w-3.5" />
                            <span className="capitalize text-xs font-gilroy font-medium">{categoryLabel}</span>
                        </div>
                    )}
                    {!initialLoading && (
                        <Button
                            onClick={handleToggleFavorite}
                            disabled={favoriteLoading}
                            size="sm"
                            className={cn(
                                "font-gilroy",
                                isFavorited
                                    ? "bg-primary text-primary-foreground hover:bg-primary/90"
                                    : "bg-gray-100/80 text-black/70 hover:bg-gray-200/80 hover:text-black"
                            )}
                        >
                            <Icon name="Star" className={`h-4 w-4 mr-2 ${isFavorited ? "fill-current" : ""}`} />
                            {favoriteLoading ? "..." : isFavorited ? "Favoriet" : "Favoriet"}
                        </Button>
                    )}
                    <ShareButton
                        location={{
                            id: location.id,
                            name: location.name,
                            category: categoryLabel || null,
                        }}
                        size="sm"
                        className="bg-green-600 hover:bg-green-700 text-white border-green-600 hover:border-green-700"
                    />
                </div>

                {/* Action buttons row: Route, Google */}
                <div className="flex items-center gap-2 flex-wrap">
                    <Button
                        asChild
                        variant="outline"
                        size="sm"
                        aria-label="Open route in Maps"
                        title="Open route in Maps"
                        className="border-white/20 text-foreground dark:text-gray-900 hover:bg-gray-200/80 hover:text-gray-800 transition-colors font-gilroy"
                    >
                        <a href={routeUrl} {...routeLinkProps}>
                            <Icon name="Navigation" className="h-4 w-4 mr-2" />
                            Route
                        </a>
                    </Button>
                    <Button
                        asChild
                        variant="outline"
                        size="sm"
                        aria-label="Search on Google"
                        title="Search on Google"
                        className="border-white/20 text-foreground dark:text-gray-900 hover:bg-gray-200/80 hover:text-gray-800 transition-colors font-gilroy"
                    >
                        <a href={googleSearchUrl} {...googleLinkProps}>
                            <Icon name="Search" className="h-4 w-4 mr-2" />
                            Google
                        </a>
                    </Button>
                </div>

                {/* Check-in button on own row, full width */}
                <div>
                    {!isAuthenticated ? (
                        <LoginPrompt message="Log in om in te checken" className="mb-0" />
                    ) : (
                        <Button
                            onClick={handleCheckIn}
                            disabled={hasCheckedInToday || isCheckingIn || initialLoading}
                            size="sm"
                            className="w-full bg-primary text-primary-foreground hover:bg-primary/90 transition-colors font-gilroy"
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
                    )}
                </div>

                {/* Rest of content */}
                {initialLoading ? (
                    <div className="text-center text-sm font-gilroy font-normal text-muted-foreground py-4">Laden...</div>
                ) : (
                    <>
                        {/* Stats Overview */}
                        <div>
                            <h3 className="text-sm font-gilroy font-medium text-foreground dark:text-gray-900 mb-3">Interacties</h3>
                            <div className="grid grid-cols-3 gap-4 text-center">
                                <div>
                                    <div className="text-2xl font-gilroy font-semibold text-primary">
                                        {checkInStats?.total_check_ins ?? 0}
                                    </div>
                                    <div className="text-xs font-gilroy font-normal text-muted-foreground dark:text-gray-900">Check-ins</div>
                                </div>
                                <div>
                                    <div className="text-2xl font-gilroy font-semibold text-primary">{totalReactions}</div>
                                    <div className="text-xs font-gilroy font-normal text-muted-foreground dark:text-gray-900">Reactions</div>
                                </div>
                                <div>
                                    <div className="text-2xl font-gilroy font-semibold text-primary">{notes.length}</div>
                                    <div className="text-xs font-gilroy font-normal text-muted-foreground dark:text-gray-900">Notities</div>
                                </div>
                            </div>
                        </div>

                        {/* Check-in Stats */}
                        {checkInStats && (
                            <div>
                                <div className="flex items-center justify-between mb-2">
                                    <h3 className="text-sm font-gilroy font-medium text-foreground dark:text-gray-900">Check-ins</h3>
                                    <Badge variant="secondary">{checkInStats.total_check_ins} totaal</Badge>
                                </div>
                                <div className="text-sm font-gilroy font-normal text-muted-foreground">
                                    {checkInStats.check_ins_today} vandaag • {checkInStats.unique_users_today} gebruikers
                                </div>
                            </div>
                        )}

                        {/* Reactions Section */}
                        <div>
                            <h3 className="text-sm font-gilroy font-medium text-foreground dark:text-gray-900 mb-3">Reactions</h3>
                            <div className="flex flex-row gap-1.5 flex-nowrap overflow-x-auto">
                                {(Object.keys(REACTION_EMOJIS) as ReactionType[]).map((reactionType) => {
                                    const count = reactionStats?.reactions[reactionType] ?? 0;
                                    const isActive = userReactions.has(reactionType);
                                    const isLoading = reactionLoading === reactionType;

                                    return (
                                        <Button
                                            key={reactionType}
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                handleReaction(reactionType);
                                            }}
                                            disabled={isLoading}
                                            variant={isActive ? "default" : "outline"}
                                            size="sm"
                                            className={cn(
                                                "relative flex-shrink-0",
                                                isActive
                                                    ? "bg-primary text-primary-foreground !bg-primary hover:!bg-primary/90 before:!hidden"
                                                    : "hover:!text-primary hover:!border-primary/50 hover:!bg-primary/10 transition-colors"
                                            )}
                                        >
                                            <span className="text-base">{REACTION_EMOJIS[reactionType]}</span>
                                            {count > 0 && (
                                                <Badge
                                                    variant="secondary"
                                                    className="ml-1 h-4 min-w-4 px-1 text-[10px] bg-transparent"
                                                >
                                                    {count}
                                                </Badge>
                                            )}
                                        </Button>
                                    );
                                })}
                            </div>
                        </div>

                        {/* Notes Section */}
                        <div>
                            <div className="flex items-center justify-between mb-3">
                                <h3 className="text-sm font-gilroy font-medium text-foreground dark:text-gray-900">Notities</h3>
                                <Button
                                    onClick={handleAddNote}
                                    size="sm"
                                    variant="outline"
                                    className="text-foreground dark:text-gray-900 hover:!bg-red-600 hover:!text-white hover:!border-red-600 transition-colors"
                                >
                                    <Icon name="Plus" className="h-4 w-4 mr-2" />
                                    Notitie toevoegen
                                </Button>
                            </div>

                            {notesLoading ? (
                                <div className="text-center text-sm font-gilroy font-normal text-muted-foreground py-4">Laden...</div>
                            ) : notes.length === 0 ? (
                                <div className="text-center text-sm font-gilroy font-normal text-muted-foreground py-4">
                                    Nog geen notities. Voeg de eerste toe!
                                </div>
                            ) : (
                                <div className="space-y-3">
                                    {notes.map((note) => (
                                        <div
                                            key={note.id}
                                            className="border rounded-lg p-3 space-y-2 bg-muted/30"
                                        >
                                            <div className="text-sm font-gilroy font-normal whitespace-pre-wrap text-foreground">{note.content}</div>
                                            <div className="flex items-center justify-between text-xs font-gilroy font-normal text-muted-foreground">
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
                                                        className="h-6 px-2 text-xs text-foreground"
                                                    >
                                                        Bewerken
                                                    </Button>
                                                    <Button
                                                        onClick={() => handleDeleteNote(note.id)}
                                                        size="sm"
                                                        variant="ghost"
                                                        className="h-6 px-2 text-xs text-destructive"
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
                        </div>
                    </>
                )}
            </div>
        </Card>
    );

    // Content for list view (with white Card container, same structure as map view)
    const listViewContent = (
        <Card className="border border-white/10 bg-white/95 backdrop-blur-sm max-w-2xl mx-auto">
            <div className="p-4 space-y-4">
                {/* Back and Report buttons - highest items */}
                <div className="flex items-center justify-between">
                    <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            onBack();
                        }}
                        className="flex items-center gap-2 text-foreground dark:text-gray-900 hover:text-primary hover:bg-transparent transition-colors font-gilroy"
                    >
                        <Icon name="ArrowUp" className="h-4 w-4" />
                        {backButtonText}
                    </Button>
                    <ReportButton
                        reportType="location"
                        targetId={locationId}
                        targetName={location.name}
                        size="sm"
                        variant="ghost"
                        className="text-foreground dark:text-gray-900 hover:text-primary hover:bg-transparent transition-colors font-gilroy"
                    />
                </div>

                {/* Title */}
                <h2 className="text-lg font-gilroy font-semibold text-foreground dark:text-gray-900">{location.name}</h2>

                {/* Category, Favorite, Share on same row */}
                <div className="flex items-center gap-2 flex-wrap">
                    {categoryLabel && CategoryIcon && (
                        <div className="flex items-center gap-2 border border-brand-red text-brand-red px-2 py-1 rounded w-fit">
                            <CategoryIcon className="h-3.5 w-3.5" />
                            <span className="capitalize text-xs font-gilroy font-medium">{categoryLabel}</span>
                        </div>
                    )}
                    {!initialLoading && (
                        <Button
                            onClick={handleToggleFavorite}
                            disabled={favoriteLoading}
                            size="sm"
                            className={cn(
                                "font-gilroy",
                                isFavorited
                                    ? "bg-primary text-primary-foreground hover:bg-primary/90"
                                    : "bg-gray-100/80 text-black/70 hover:bg-gray-200/80 hover:text-black"
                            )}
                        >
                            <Icon name="Star" className={`h-4 w-4 mr-2 ${isFavorited ? "fill-current" : ""}`} />
                            {favoriteLoading ? "..." : isFavorited ? "Favoriet" : "Favoriet"}
                        </Button>
                    )}
                    <ShareButton
                        location={{
                            id: location.id,
                            name: location.name,
                            category: categoryLabel || null,
                        }}
                        size="sm"
                        className="bg-green-600 hover:bg-green-700 text-white border-green-600 hover:border-green-700"
                    />
                </div>

                {/* Action buttons row: Route, Google */}
                <div className="flex items-center gap-2 flex-wrap">
                    <Button
                        asChild
                        variant="outline"
                        size="sm"
                        aria-label="Open route in Maps"
                        title="Open route in Maps"
                        className="border-white/20 text-foreground dark:text-gray-900 hover:bg-gray-200/80 hover:text-gray-800 transition-colors font-gilroy"
                    >
                        <a href={routeUrl} {...routeLinkProps}>
                            <Icon name="Navigation" className="h-4 w-4 mr-2" />
                            Route
                        </a>
                    </Button>
                    <Button
                        asChild
                        variant="outline"
                        size="sm"
                        aria-label="Search on Google"
                        title="Search on Google"
                        className="border-white/20 text-foreground dark:text-gray-900 hover:bg-gray-200/80 hover:text-gray-800 transition-colors font-gilroy"
                    >
                        <a href={googleSearchUrl} {...googleLinkProps}>
                            <Icon name="Search" className="h-4 w-4 mr-2" />
                            Google
                        </a>
                    </Button>
                </div>

                {/* Check-in button on own row, full width */}
                {!initialLoading && (
                    <div>
                        {!isAuthenticated ? (
                            <LoginPrompt message="Log in om in te checken" className="mb-0" />
                        ) : (
                            <Button
                                onClick={handleCheckIn}
                                disabled={hasCheckedInToday || isCheckingIn}
                                size="sm"
                                className="w-full bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
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
                        )}
                    </div>
                )}

                {/* Rest of content */}
                {initialLoading ? (
                    <div className="text-center text-sm font-gilroy font-normal text-muted-foreground py-4">Laden...</div>
                ) : (
                    <>

                        {/* Stats Overview */}
                        <div>
                            <h3 className="text-sm font-gilroy font-medium text-foreground dark:text-gray-900 mb-3">Interacties</h3>
                            <div className="grid grid-cols-3 gap-4 text-center">
                                <div>
                                    <div className="text-2xl font-gilroy font-semibold text-primary">
                                        {checkInStats?.total_check_ins ?? 0}
                                    </div>
                                    <div className="text-xs font-gilroy font-normal text-muted-foreground dark:text-gray-900">Check-ins</div>
                                </div>
                                <div>
                                    <div className="text-2xl font-gilroy font-semibold text-primary">{totalReactions}</div>
                                    <div className="text-xs font-gilroy font-normal text-muted-foreground dark:text-gray-900">Reactions</div>
                                </div>
                                <div>
                                    <div className="text-2xl font-gilroy font-semibold text-primary">{notes.length}</div>
                                    <div className="text-xs font-gilroy font-normal text-muted-foreground dark:text-gray-900">Notities</div>
                                </div>
                            </div>
                        </div>

                        {/* Check-in Stats */}
                        {checkInStats && (
                            <div>
                                <div className="flex items-center justify-between mb-2">
                                    <h3 className="text-sm font-gilroy font-medium text-foreground dark:text-gray-900">Check-ins</h3>
                                    <Badge variant="secondary">{checkInStats.total_check_ins} totaal</Badge>
                                </div>
                                <div className="text-sm font-gilroy font-normal text-muted-foreground">
                                    {checkInStats.check_ins_today} vandaag • {checkInStats.unique_users_today} gebruikers
                                </div>
                            </div>
                        )}

                        {/* Reactions Section */}
                        <div>
                            <h3 className="text-sm font-gilroy font-medium text-foreground dark:text-gray-900 mb-3">Reactions</h3>
                            <div className="flex flex-row gap-1.5 flex-nowrap overflow-x-auto">
                                {(Object.keys(REACTION_EMOJIS) as ReactionType[]).map((reactionType) => {
                                    const count = reactionStats?.reactions[reactionType] ?? 0;
                                    const isActive = userReactions.has(reactionType);
                                    const isLoading = reactionLoading === reactionType;

                                    return (
                                        <Button
                                            key={reactionType}
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                handleReaction(reactionType);
                                            }}
                                            disabled={isLoading}
                                            variant={isActive ? "default" : "outline"}
                                            size="sm"
                                            className={cn(
                                                "relative flex-shrink-0",
                                                isActive
                                                    ? "bg-primary text-primary-foreground !bg-primary hover:!bg-primary/90 before:!hidden"
                                                    : "hover:!text-primary hover:!border-primary/50 hover:!bg-primary/10 transition-colors"
                                            )}
                                        >
                                            <span className="text-base">{REACTION_EMOJIS[reactionType]}</span>
                                            {count > 0 && (
                                                <Badge
                                                    variant="secondary"
                                                    className="ml-1 h-4 min-w-4 px-1 text-[10px] bg-transparent"
                                                >
                                                    {count}
                                                </Badge>
                                            )}
                                        </Button>
                                    );
                                })}
                            </div>
                        </div>

                        {/* Notes Section */}
                        <div>
                            <div className="flex items-center justify-between mb-3">
                                <h3 className="text-sm font-gilroy font-medium text-foreground">Notities</h3>
                                <Button
                                    onClick={handleAddNote}
                                    size="sm"
                                    variant="outline"
                                    className="text-foreground hover:!bg-red-600 hover:!text-white hover:!border-red-600 transition-colors"
                                >
                                    <Icon name="Plus" className="h-4 w-4 mr-2" />
                                    Notitie toevoegen
                                </Button>
                            </div>

                            {notesLoading ? (
                                <div className="text-center text-sm font-gilroy font-normal text-muted-foreground py-4">Laden...</div>
                            ) : notes.length === 0 ? (
                                <div className="text-center text-sm font-gilroy font-normal text-muted-foreground py-4">
                                    Nog geen notities. Voeg de eerste toe!
                                </div>
                            ) : (
                                <div className="space-y-3">
                                    {notes.map((note) => (
                                        <div
                                            key={note.id}
                                            className="border rounded-lg p-3 space-y-2 bg-muted/30"
                                        >
                                            <div className="text-sm font-gilroy font-normal whitespace-pre-wrap text-foreground">{note.content}</div>
                                            <div className="flex items-center justify-between text-xs font-gilroy font-normal text-muted-foreground">
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
                                                        className="h-6 px-2 text-xs text-foreground"
                                                    >
                                                        Bewerken
                                                    </Button>
                                                    <Button
                                                        onClick={() => handleDeleteNote(note.id)}
                                                        size="sm"
                                                        variant="ghost"
                                                        className="h-6 px-2 text-xs text-destructive"
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
                        </div>
                    </>
                )}
            </div>
        </Card>
    );

    // Render based on view mode
    if (viewMode === "map") {
        return (
            <DialogPrimitive.Root open={Boolean(open)} onOpenChange={(next) => { if (!next && onClose) onClose(); }}>
                <DialogPrimitive.Portal>
                    <DialogPrimitive.Overlay
                        className={cn(
                            "fixed inset-0 z-[55] bg-black/10",
                            "pointer-events-none data-[state=open]:pointer-events-auto",
                            "data-[state=closed]:animate-out data-[state=closed]:fade-out-0",
                            "data-[state=open]:animate-in data-[state=open]:fade-in-0",
                        )}
                    />
                    <DialogPrimitive.Content
                        className={cn(
                            "fixed inset-x-0 bottom-0 top-auto z-[60] mx-auto w-full max-w-2xl",
                            "flex max-h-[calc(100vh-120px)] flex-col rounded-t-[40px] border border-white/15 bg-surface-raised/95 text-foreground shadow-[0_-40px_80px_rgba(0,0,0,0.6)] backdrop-blur-2xl",
                            "px-5 pt-6 pb-[calc(env(safe-area-inset-bottom)+20px)]",
                            "focus:outline-none data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:slide-in-from-bottom",
                            "data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:slide-out-to-bottom",
                            "lg:left-1/2 lg:right-auto lg:top-1/2 lg:bottom-auto lg:max-h-[85vh] lg:w-[min(90vw,960px)] lg:max-w-[min(90vw,960px)] lg:-translate-x-1/2 lg:-translate-y-1/2",
                            "lg:rounded-[40px] lg:px-6 lg:pb-6 lg:shadow-[0_45px_90px_rgba(0,0,0,0.6)]",
                            "lg:data-[state=open]:zoom-in-95 lg:data-[state=closed]:zoom-out-95",
                            "overflow-y-auto",
                        )}
                        aria-labelledby="unified-detail-title"
                        aria-describedby="unified-detail-description"
                    >
                        <div id="unified-detail-description">
                            {mapViewContent}
                        </div>
                    </DialogPrimitive.Content>
                </DialogPrimitive.Portal>
            </DialogPrimitive.Root>
        );
    }

    // List view - normale div
    return (
        <>
            <div className="flex flex-col h-full px-5 pt-6">
                {listViewContent}
            </div>
            {/* Note Dialog - alleen voor list view */}
            <NoteDialog
                open={isNoteDialogOpen}
                onOpenChange={setIsNoteDialogOpen}
                onSubmit={handleSaveNote}
                initialContent={editingNote?.content || ""}
                locationName={location.name}
            />
        </>
    );
}







