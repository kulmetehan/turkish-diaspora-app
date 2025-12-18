import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogFooter,
    DialogHeader,
    DialogTitle
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useEffect, useState } from "react";

type Props = {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSubmit: (content: string) => Promise<void>;
    initialContent?: string;
    locationName?: string;
};

const MIN_LENGTH = 3;
const MAX_LENGTH = 1000;

export default function NoteDialog({
    open,
    onOpenChange,
    onSubmit,
    initialContent = "",
    locationName,
}: Props) {
    const [content, setContent] = useState(initialContent);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const characterCount = content.length;
    const isValid = characterCount >= MIN_LENGTH && characterCount <= MAX_LENGTH;

    const handleSubmit = async () => {
        if (!isValid) {
            setError(`Note moet tussen ${MIN_LENGTH} en ${MAX_LENGTH} karakters zijn`);
            return;
        }

        setError(null);
        setIsSubmitting(true);

        try {
            await onSubmit(content);
            setContent("");
            onOpenChange(false);
        } catch (err: any) {
            setError(err?.message || "Fout bij opslaan van notitie");
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleOpenChange = (newOpen: boolean) => {
        if (!newOpen && !isSubmitting) {
            setContent(initialContent);
            setError(null);
        }
        onOpenChange(newOpen);
    };

    // Reset content when dialog opens with new initialContent
    // Moved to useEffect to prevent blocking input during typing
    useEffect(() => {
        if (open && initialContent !== content && !isSubmitting) {
            setContent(initialContent);
            setError(null);
        }
    }, [open, initialContent]); // Only run when these change, not on every render

    // Fix: Restore body pointer-events to allow keyboard input
    // Radix UI sets body to pointer-events: none to prevent scrolling,
    // but this also blocks keyboard events. We restore it while keeping overflow hidden.
    useEffect(() => {
        if (open) {
            const body = document.body;
            const originalPointerEvents = body.style.pointerEvents;
            const originalOverflow = body.style.overflow;
            const originalAriaHidden = body.getAttribute('aria-hidden');

            // Use requestAnimationFrame to let Radix set its styles first
            const timer = requestAnimationFrame(() => {
                // Restore pointer events to allow keyboard input
                body.style.pointerEvents = 'auto';
                // Keep overflow hidden to prevent scrolling
                body.style.overflow = 'hidden';
                // Remove aria-hidden if present (blocks keyboard events)
                if (originalAriaHidden) {
                    body.removeAttribute('aria-hidden');
                }
            });

            return () => {
                cancelAnimationFrame(timer);
                body.style.pointerEvents = originalPointerEvents;
                body.style.overflow = originalOverflow;
                if (originalAriaHidden) {
                    body.setAttribute('aria-hidden', originalAriaHidden);
                }
            };
        }
    }, [open]);

    return (
        <Dialog open={open} onOpenChange={handleOpenChange}>
            <DialogContent
                className="z-[80] font-gilroy"
                overlayClassName="z-[79]"
                onEscapeKeyDown={(e) => {
                    // Prevent closing on Escape when typing in textarea
                    if (document.activeElement?.tagName === 'TEXTAREA') {
                        e.preventDefault();
                    }
                }}
                onOpenAutoFocus={(e) => {
                    // Don't prevent default - let Radix handle focus naturally
                    const textarea = document.getElementById('note-content');
                    if (textarea) {
                        requestAnimationFrame(() => {
                            (textarea as HTMLTextAreaElement).focus();
                        });
                    }
                }}
            >
                <DialogHeader>
                    <DialogTitle className="font-gilroy">
                        {initialContent ? "Notitie bewerken" : "Notitie toevoegen"}
                        {locationName && ` - ${locationName}`}
                    </DialogTitle>
                </DialogHeader>

                <div className="space-y-4 py-4">
                    <div className="space-y-2">
                        <Label htmlFor="note-content">Notitie</Label>
                        <Textarea
                            id="note-content"
                            value={content}
                            onChange={(e) => {
                                setContent(e.target.value);
                                setError(null);
                            }}
                            placeholder="Schrijf je notitie hier..."
                            rows={6}
                            maxLength={MAX_LENGTH}
                            disabled={isSubmitting}
                            autoFocus
                            className="font-gilroy"
                        />
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                            <span>
                                {error ? (
                                    <span className="text-destructive">{error}</span>
                                ) : (
                                    <span>
                                        {characterCount < MIN_LENGTH
                                            ? `Minimaal ${MIN_LENGTH - characterCount} karakters nodig`
                                            : isValid
                                                ? "✓"
                                                : `${characterCount - MAX_LENGTH} karakters te veel`}
                                    </span>
                                )}
                            </span>
                            <span>
                                {characterCount} / {MAX_LENGTH}
                            </span>
                        </div>
                    </div>
                </div>

                <DialogFooter>
                    <Button
                        type="button"
                        variant="outline"
                        onClick={() => handleOpenChange(false)}
                        disabled={isSubmitting}
                        className="font-gilroy"
                    >
                        Annuleren
                    </Button>
                    <Button
                        type="button"
                        variant="default"
                        onClick={handleSubmit}
                        disabled={!isValid || isSubmitting}
                        className="font-gilroy"
                    >
                        {isSubmitting ? "Opslaan..." : initialContent ? "Bijwerken" : "Opslaan"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

