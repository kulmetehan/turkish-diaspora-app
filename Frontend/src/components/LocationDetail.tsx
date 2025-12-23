import type { LocationMarker } from "@/api/fetchLocations";
import { Icon } from "@/components/Icon";
import NoteDialog from "@/components/location/NoteDialog";
import { ReportButton } from "@/components/report/ReportButton";
import { ShareButton } from "@/components/share/ShareButton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmojiPicker } from "@/components/ui/EmojiPicker";
import { VerifiedBadge } from "@/components/VerifiedBadge";
import {
    addFavorite,
    createCheckIn,
    createNote,
    deleteNote,
    getCheckInStats,
    getLocationMahallelisi,
    getLocationReactions,
    getNotes,
    isFavorite,
    removeFavorite,
    toggleLocationReaction,
    updateNote,
    type CheckInStats,
    type MahallelisiResponse,
    type NoteResponse,
    type ReactionStats,
    type ReactionType,
} from "@/lib/api";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { roleDisplayName } from "@/lib/roleDisplay";
import { labelDisplayName } from "@/lib/labelDisplay";
import { useMascotteFeedback } from "@/hooks/useMascotteFeedback";

type Props = {
    location: LocationMarker;
    onBackToList: () => void;
};

// No longer using fixed reaction types - reactions are now custom emoji strings

export default function LocationDetail({ location, onBackToList }: Props) {
    const locationId = parseInt(location.id);
    const { showMascotteFeedback } = useMascotteFeedback();

    // State for check-ins
    const [checkInStats, setCheckInStats] = useState<CheckInStats | null>(null);
    const [hasCheckedInToday, setHasCheckedInToday] = useState(false);
    const [isCheckingIn, setIsCheckingIn] = useState(false);

    // State for reactions
    const [reactionStats, setReactionStats] = useState<ReactionStats | null>(null);
    const [userReaction, setUserReaction] = useState<ReactionType | null>(null);
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

    // State for mahallelisi
    const [mahallelisi, setMahallelisi] = useState<MahallelisiResponse | null>(null);

    // State for loading initial data
    const [initialLoading, setInitialLoading] = useState(true);

    // Track notes created by user in this session (for popular note detection)
    const userCreatedNotesRef = useRef<Set<number>>(new Set());
    const popularNotesNotifiedRef = useRef<Set<number>>(new Set());

    // Check for popular notes when notes are updated
    useEffect(() => {
        // Check if any user-created notes have reached >= 5 reactions
        userCreatedNotesRef.current.forEach((noteId) => {
            // Skip if already notified
            if (popularNotesNotifiedRef.current.has(noteId)) {
                return;
            }

            const note = notes.find((n) => n.id === noteId);
            if (note && (note.reaction_count || 0) >= 5) {
                showMascotteFeedback("note_popular");
                popularNotesNotifiedRef.current.add(noteId);
            }
        });
    }, [notes, showMascotteFeedback]);

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
                const reactionData = await getLocationReactions(locationId);
                setReactionStats({
                    location_id: locationId,
                    reactions: reactionData.reactions,
                });
                // Set user reaction from API response
                setUserReaction(reactionData.user_reaction || null);

                // Load notes (sorted by reactions by default)
                const notesData = await getNotes(locationId, 50, 0, "reactions_desc");
                setNotes(notesData);

                // Check favorite status
                const favorited = await isFavorite(locationId);
                setIsFavorited(favorited);

                // Load mahallelisi
                try {
                    const mahallelisiData = await getLocationMahallelisi(locationId);
                    setMahallelisi(mahallelisiData);
                } catch (error: any) {
                    console.error("Failed to load mahallelisi:", error);
                    // Don't show error toast, just silently fail
                }
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
            // Show mascotte feedback
            showMascotteFeedback("check_in");
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

        const hasReaction = userReaction === reactionType;
        setReactionLoading(reactionType);

        try {
            // Toggle reaction (add if not exists, remove if exists)
            const result = await toggleLocationReaction(locationId, reactionType);

            // Update user reaction based on result
            setUserReaction(result.is_active ? reactionType : null);

            // Refresh stats
            const stats = await getLocationReactions(locationId);
            setReactionStats({
                location_id: locationId,
                reactions: stats.reactions,
            });
            setUserReaction(stats.user_reaction || null);
        } catch (error: any) {
            toast.error(error.message || "Fout bij bijwerken van reaction");
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
                // Track this note as user-created for popular note detection
                userCreatedNotesRef.current.add(newNote.id);
                // Replace temporary note with real one from server
                setNotes((prevNotes) =>
                    prevNotes.map((note) => (note.id === tempNote.id ? newNote : note))
                );
                toast.success("Notitie toegevoegd");
                // Show mascotte feedback
                showMascotteFeedback("note_created");
            }

            setIsNoteDialogOpen(false);
            setEditingNote(null);
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
                            <div className="flex flex-col gap-1 flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                    <h2 className="text-xl font-semibold">{location.name}</h2>
                                    {location.has_verified_badge && <VerifiedBadge size="md" />}
                                </div>
                                {checkInStats?.status_text && (
                                    <p className="text-sm text-foreground/60 italic">{checkInStats.status_text}</p>
                                )}
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

                        {/* Mahallelisi Card */}
                        <Card className="p-4 mb-4">
                            <h3 className="font-medium text-sm mb-3">Bu haftanın Mahallelisi</h3>
                            {mahallelisi ? (
                                <div className="space-y-1">
                                    <div className="flex items-center gap-2">
                                        <span className="font-medium">{mahallelisi.name}</span>
                                        {mahallelisi.primary_role && (
                                            <Badge variant="secondary" className="text-xs">
                                                {roleDisplayName(mahallelisi.primary_role)}
                                            </Badge>
                                        )}
                                    </div>
                                    {mahallelisi.secondary_role && (
                                        <Badge variant="outline" className="text-xs">
                                            {roleDisplayName(mahallelisi.secondary_role)}
                                        </Badge>
                                    )}
                                </div>
                            ) : (
                                <p className="text-sm text-foreground/60">
                                    Bu hafta henüz kimse uğramadı
                                </p>
                            )}
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

                        {/* Activity Section */}
                        {checkInStats && checkInStats.check_ins_today > 0 && (
                            <Card className="p-4 mb-4">
                                <h3 className="font-medium text-sm mb-2">Aktiviteit</h3>
                                <p className="text-sm text-foreground/70">
                                    Bugün {checkInStats.unique_users_today} kişi uğradı
                                </p>
                            </Card>
                        )}

                        {/* Reactions Section */}
                        <Card className="p-4 mb-4">
                            <div className="flex items-center justify-between mb-3">
                                <h3 className="font-medium text-sm">Reactions</h3>
                                <EmojiPicker
                                    onEmojiSelect={handleReaction}
                                    className="text-foreground"
                                />
                            </div>
                            <div className="flex flex-wrap gap-2">
                                {reactionStats?.reactions && Object.entries(reactionStats.reactions).map(([emoji, count]) => {
                                    if (count === 0) return null;
                                    const isActive = userReaction === emoji;
                                    const isLoading = reactionLoading === emoji;

                                    return (
                                        <Button
                                            key={emoji}
                                            onClick={() => handleReaction(emoji)}
                                            disabled={isLoading}
                                            variant={isActive ? "default" : "outline"}
                                            size="sm"
                                            className="relative"
                                        >
                                            <span className="text-lg mr-1">{emoji}</span>
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
                                {(!reactionStats?.reactions || Object.keys(reactionStats.reactions).length === 0) && (
                                    <p className="text-sm text-muted-foreground">Nog geen reacties. Voeg de eerste toe!</p>
                                )}
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
                                            {note.labels && note.labels.length > 0 && (
                                                <div className="flex flex-wrap gap-1">
                                                    {note.labels.map((label) => (
                                                        <Badge
                                                            key={label}
                                                            variant="secondary"
                                                            className="text-xs"
                                                        >
                                                            {labelDisplayName(label)}
                                                        </Badge>
                                                    ))}
                                                </div>
                                            )}
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
