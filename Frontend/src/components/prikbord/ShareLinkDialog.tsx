// Frontend/src/components/prikbord/ShareLinkDialog.tsx
import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createSharedLink } from "@/lib/api/prikbord";
import { useEffect, useState } from "react";
import { toast } from "sonner";

interface ShareLinkDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSuccess?: () => void;
}

export function ShareLinkDialog({
    open,
    onOpenChange,
    onSuccess,
}: ShareLinkDialogProps) {
    const [url, setUrl] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [preview, setPreview] = useState<{
        title?: string;
        description?: string;
        image_url?: string;
    } | null>(null);
    const [manualEdit, setManualEdit] = useState(false);
    const [manualTitle, setManualTitle] = useState("");
    const [manualDescription, setManualDescription] = useState("");
    const [manualImageUrl, setManualImageUrl] = useState("");

    useEffect(() => {
        if (!open) {
            setUrl("");
            setPreview(null);
            setManualEdit(false);
            setManualTitle("");
            setManualDescription("");
            setManualImageUrl("");
        }
    }, [open]);

    const handleSubmit = async () => {
        if (!url.trim()) {
            toast.error("Voer een URL in");
            return;
        }

        // Basic URL validation
        try {
            new URL(url.startsWith("http") ? url : `https://${url}`);
        } catch {
            toast.error("Ongeldige URL");
            return;
        }

        // If manual edit mode, validate that at least title or description is provided
        if (manualEdit && !manualTitle.trim() && !manualDescription.trim()) {
            toast.error("Voer minstens een titel of beschrijving in");
            return;
        }

        setIsSubmitting(true);
        try {
            await createSharedLink({
                url: url.trim(),
                ...(manualEdit && {
                    title: manualTitle.trim() || undefined,
                    description: manualDescription.trim() || undefined,
                    image_url: manualImageUrl.trim() || undefined,
                }),
            });
            toast.success("Link gedeeld!");
            onOpenChange(false);
            onSuccess?.();
        } catch (err: any) {
            toast.error("Kon link niet delen", {
                description: err.message || "Er is een fout opgetreden",
            });
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-md">
                <DialogHeader>
                    <DialogTitle>Deel een link</DialogTitle>
                    <DialogDescription>
                        Plak hier een link van Marktplaats, Instagram, YouTube, Facebook of
                        een andere website. Als de preview niet goed werkt, kun je handmatig
                        een titel, beschrijving en afbeelding toevoegen.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4">
                    <div className="space-y-2">
                        <Label htmlFor="url">URL</Label>
                        <Input
                            id="url"
                            type="url"
                            placeholder="https://..."
                            value={url}
                            onChange={(e) => setUrl(e.target.value)}
                            disabled={isSubmitting}
                        />
                    </div>

                    {url.trim() && !manualEdit && !preview && (
                        <div className="rounded-lg border border-border p-3 space-y-2">
                            <p className="text-sm text-muted-foreground">
                                Je kunt de preview automatisch laten genereren of handmatig bewerken.
                            </p>
                            <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                onClick={() => setManualEdit(true)}
                                className="w-full mt-2"
                            >
                                <Icon name="Edit" className="h-4 w-4 mr-2" />
                                Preview handmatig bewerken
                            </Button>
                        </div>
                    )}

                    {preview && !manualEdit && (
                        <div className="rounded-lg border border-border p-3 space-y-2">
                            {preview.image_url && (
                                <img
                                    src={preview.image_url}
                                    alt="Preview"
                                    className="w-full h-32 object-cover rounded"
                                />
                            )}
                            {preview.title && (
                                <p className="font-semibold text-sm">{preview.title}</p>
                            )}
                            {preview.description && (
                                <p className="text-xs text-muted-foreground line-clamp-2">
                                    {preview.description}
                                </p>
                            )}
                            <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                onClick={() => setManualEdit(true)}
                                className="w-full mt-2"
                            >
                                <Icon name="Edit" className="h-4 w-4 mr-2" />
                                Preview niet goed? Bewerk handmatig
                            </Button>
                        </div>
                    )}

                    {manualEdit && (
                        <div className="rounded-lg border border-border p-3 space-y-3">
                            <div className="flex items-center justify-between">
                                <Label className="text-sm font-medium">Handmatige preview</Label>
                                <Button
                                    type="button"
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => setManualEdit(false)}
                                >
                                    <Icon name="X" className="h-4 w-4" />
                                </Button>
                            </div>
                            <div className="space-y-2">
                                <div>
                                    <Label htmlFor="manual-title">Titel</Label>
                                    <Input
                                        id="manual-title"
                                        value={manualTitle}
                                        onChange={(e) => setManualTitle(e.target.value)}
                                        placeholder="Voer een titel in"
                                        disabled={isSubmitting}
                                    />
                                </div>
                                <div>
                                    <Label htmlFor="manual-description">Beschrijving</Label>
                                    <Input
                                        id="manual-description"
                                        value={manualDescription}
                                        onChange={(e) => setManualDescription(e.target.value)}
                                        placeholder="Voer een beschrijving in"
                                        disabled={isSubmitting}
                                    />
                                </div>
                                <div>
                                    <Label htmlFor="manual-image">Afbeelding URL (optioneel)</Label>
                                    <Input
                                        id="manual-image"
                                        type="url"
                                        value={manualImageUrl}
                                        onChange={(e) => setManualImageUrl(e.target.value)}
                                        placeholder="https://..."
                                        disabled={isSubmitting}
                                    />
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                <DialogFooter>
                    <Button
                        variant="outline"
                        onClick={() => onOpenChange(false)}
                        disabled={isSubmitting}
                    >
                        Annuleren
                    </Button>
                    <Button onClick={handleSubmit} disabled={isSubmitting || !url.trim()}>
                        {isSubmitting ? (
                            <>
                                <Icon name="Loader2" className="h-4 w-4 mr-2 animate-spin" />
                                Delen...
                            </>
                        ) : (
                            <>
                                <Icon name="Share2" className="h-4 w-4 mr-2" />
                                Delen
                            </>
                        )}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

