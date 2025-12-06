import type { LocationMarker } from "@/api/fetchLocations";
import { Icon } from "@/components/Icon";
import NoteDialog from "@/components/location/NoteDialog";
import { ReportButton } from "@/components/report/ReportButton";
import { ShareButton } from "@/components/share/ShareButton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { VerifiedBadge } from "@/components/VerifiedBadge";
import {
    addFavorite,
    createCheckIn,
    createNote,
    createReaction,
    deleteNote,
    getCheckInStats,
    getNotes,
    getReactionStats,
    isFavorite,
    removeFavorite,
    removeReaction,
    updateNote,
    type CheckInStats,
    type NoteResponse,
    type ReactionStats,
    type ReactionType,
} from "@/lib/api";
import { useEffect, useState } from "react";
import { toast } from "sonner";

type Props = {
    location: LocationMarker;
    onBackToList: () => void;
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

export default function LocationDetail({ location, onBackToList }: Props) {
    const locationId = parseInt(location.id);

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
        const loadData = async () => {
            setInitialLoading(true);
            try {
                // Load check-in stats
                const checkInData = await getCheckInStats(locationId);
                setCheckInStats(checkInData);
                setHasCheckedInToday(checkInData.check_ins_today > 0);

                // Load reaction stats
                const reactionData = await getReactionStats(locationId);
                setReactionStats(reactionData);
                // Note: We can't determine user reactions without user_id, so we'll track locally

                // Load notes
                const notesData = await getNotes(locationId);
                setNotes(notesData);

                // Check favorite status
                const favorited = await isFavorite(locationId);
                setIsFavorited(favorited);
            } catch (error: any) {
                console.error("Failed to load location data:", error);
                toast.error("Fout bij laden van locatie data");
            } finally {
                setInitialLoading(false);
            }
        };

        loadData();
    }, [locationId]);

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
            if (hasReaction) {
                // Remove reaction
                await removeReaction(locationId, reactionType);
                setUserReactions((prev) => {
                    const next = new Set(prev);
                    next.delete(reactionType);
                    return next;
                });
                toast.success("Reaction verwijderd");
            } else {
                // Add reaction
                await createReaction(locationId, reactionType);
                setUserReactions((prev) => new Set(prev).add(reactionType));
                toast.success("Reaction toegevoegd");
            }

            // Refresh stats
            const stats = await getReactionStats(locationId);
            setReactionStats(stats);
        } catch (error: any) {
            if (error.message?.includes("409") || error.message?.includes("already exists")) {
                // If we tried to add but it already exists, add it to userReactions
                if (!hasReaction) {
                    setUserReactions((prev) => new Set(prev).add(reactionType));
                }
                toast.error("Je hebt al gereageerd met deze emoji");
            } else {
                toast.error(error.message || "Fout bij toevoegen van reaction");
            }
        } finally {
            setReactionLoading(null);
        }
    };

    // Note handlers
    const handleAddNote = () => {
        setEditingNote(null);
        setIsNoteDialogOpen(true);
    };

    const handleEditNote = (note: NoteResponse) => {
        setEditingNote(note);
        setIsNoteDialogOpen(true);
    };

    const handleSaveNote = async (content: string) => {
        try {
            if (editingNote) {
                await updateNote(editingNote.id, content);
                toast.success("Notitie bijgewerkt");
            } else {
                await createNote(locationId, content);
                toast.success("Notitie toegevoegd");
            }

            // Refresh notes
            const notesData = await getNotes(locationId);
            setNotes(notesData);
            setIsNoteDialogOpen(false);
            setEditingNote(null);
        } catch (error: any) {
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
        <div className="flex flex-col h-full">
            {/* Header with back button */}
            <div className="flex items-center gap-3 p-4 border-b bg-background">
                <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        onBackToList();
                    }}
                    className="flex items-center gap-2"
                >
                    <Icon name="ArrowLeft" className="h-4 w-4" />
                    Back to List
                </Button>
                <div className="flex-1" />
                <div className="flex items-center gap-2">
                    <ReportButton
                        reportType="location"
                        targetId={locationId}
                        targetName={location.name}
                        size="sm"
                    />
                    <ShareButton
                        location={{
                            id: location.id,
                            name: location.name,
                            category: location.category_label || location.category || null,
                        }}
                        size="sm"
                    />
                </div>
            </div>

            {/* Location content */}
            <div className="flex-1 overflow-auto p-4">
                {/* Location Info Card */}
                <Card className="p-4 mb-4">
                    <div className="space-y-3">
                        {/* Name */}
                        <div className="flex items-start justify-between">
                            <div className="flex items-center gap-2 flex-1 min-w-0">
                                <h2 className="text-xl font-semibold">{location.name}</h2>
                                {location.has_verified_badge && <VerifiedBadge size="md" />}
                            </div>
                        </div>

                        {/* Category */}
                        {(location.category_label || location.category) && (
                            <div className="flex items-center gap-2 text-sm text-foreground/70">
                                <Icon name="Tag" className="h-4 w-4" />
                                <span className="capitalize">{location.category_label ?? location.category}</span>
                            </div>
                        )}

                        {/* Confidence score */}
                        {typeof location.confidence_score === "number" && (
                            <div className="flex items-center gap-2 text-sm text-foreground/70">
                                <Icon name="Target" className="h-4 w-4" />
                                <span>AI Confidence: {(location.confidence_score * 100).toFixed(0)}%</span>
                            </div>
                        )}

                        {/* State */}
                        {location.state && (
                            <div className="flex items-center gap-2 text-sm text-foreground/70">
                                <Icon name="MapPin" className="h-4 w-4" />
                                <span className="capitalize">{location.state}</span>
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
                        <Card className="p-4 mb-4">
                            <div className="flex items-center gap-2 flex-wrap">
                                <Button
                                    onClick={handleCheckIn}
                                    disabled={hasCheckedInToday || isCheckingIn}
                                    variant={hasCheckedInToday ? "secondary" : "default"}
                                    size="sm"
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
                                    className="text-foreground"
                                >
                                    <Icon name="Star" className={`h-4 w-4 mr-2 ${isFavorited ? "fill-current" : ""}`} />
                                    {favoriteLoading ? "..." : isFavorited ? "Favoriet" : "Favoriet"}
                                </Button>
                            </div>
                        </Card>

                        {/* Stats Overview Card */}
                        <Card className="p-4 mb-4">
                            <h3 className="font-medium text-sm mb-3">Interacties</h3>
                            <div className="grid grid-cols-3 gap-4 text-center">
                                <div>
                                    <div className="text-2xl font-bold">
                                        {checkInStats?.total_check_ins ?? 0}
                                    </div>
                                    <div className="text-xs text-foreground/70">Check-ins</div>
                                </div>
                                <div>
                                    <div className="text-2xl font-bold">{totalReactions}</div>
                                    <div className="text-xs text-foreground/70">Reactions</div>
                                </div>
                                <div>
                                    <div className="text-2xl font-bold">{notes.length}</div>
                                    <div className="text-xs text-foreground/70">Notities</div>
                                </div>
                            </div>
                        </Card>

                        {/* Check-in Stats Card */}
                        {checkInStats && (
                            <Card className="p-4 mb-4">
                                <div className="flex items-center justify-between mb-2">
                                    <h3 className="font-medium text-sm">Check-ins</h3>
                                    <Badge variant="secondary">{checkInStats.total_check_ins} totaal</Badge>
                                </div>
                                <div className="text-sm text-foreground/70">
                                    {checkInStats.check_ins_today} vandaag • {checkInStats.unique_users_today} gebruikers
                                </div>
                            </Card>
                        )}

                        {/* Reactions Section */}
                        <Card className="p-4 mb-4">
                            <h3 className="font-medium text-sm mb-3">Reactions</h3>
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
                                            className="relative"
                                        >
                                            <span className="text-lg mr-1">{REACTION_EMOJIS[reactionType]}</span>
                                            <span className="text-xs">{REACTION_LABELS[reactionType]}</span>
                                            {count > 0 && (
                                                <Badge
                                                    variant="secondary"
                                                    className="ml-2 h-5 min-w-5 px-1.5 text-xs"
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
                        <Card className="p-4 mb-4">
                            <div className="flex items-center justify-between mb-3">
                                <h3 className="font-medium text-sm">Notities</h3>
                                <Button onClick={handleAddNote} size="sm" variant="outline" className="text-foreground">
                                    <Icon name="Plus" className="h-4 w-4 mr-2" />
                                    Notitie toevoegen
                                </Button>
                            </div>

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
                                            <div className="flex items-center justify-between text-xs text-foreground/60">
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
                        </Card>
                    </>
                )}
            </div>

            {/* Note Dialog */}
            <NoteDialog
                open={isNoteDialogOpen}
                onOpenChange={setIsNoteDialogOpen}
                onSubmit={handleSaveNote}
                initialContent={editingNote?.content || ""}
                locationName={location.name}
            />
        </div>
    );
}
