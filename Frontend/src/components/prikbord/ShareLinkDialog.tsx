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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { createSharedLink } from "@/lib/api/prikbord";
import { uploadMedia, createMediaPreview, type MediaUploadResult } from "@/lib/mediaUpload";
import { useEffect, useState, useRef } from "react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

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
    const [postType, setPostType] = useState<"link" | "media">("link");
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
    
    // Media upload state
    const [mediaFiles, setMediaFiles] = useState<File[]>([]);
    const [mediaPreviews, setMediaPreviews] = useState<string[]>([]);
    const [uploadedMediaUrls, setUploadedMediaUrls] = useState<string[]>([]);
    const [isUploading, setIsUploading] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        if (!open) {
            setPostType("link");
            setUrl("");
            setPreview(null);
            setManualEdit(false);
            setManualTitle("");
            setManualDescription("");
            setManualImageUrl("");
            setMediaFiles([]);
            setMediaPreviews([]);
            setUploadedMediaUrls([]);
        }
    }, [open]);

    // Handle file selection
    const handleFileSelect = async (files: FileList | null) => {
        if (!files || files.length === 0) return;

        const newFiles = Array.from(files);
        const newPreviews: string[] = [];

        // Create previews for all files
        for (const file of newFiles) {
            try {
                const preview = await createMediaPreview(file);
                newPreviews.push(preview);
            } catch (error) {
                console.error("Failed to create preview:", error);
                toast.error(`Kon preview niet maken voor ${file.name}`);
            }
        }

        setMediaFiles((prev) => [...prev, ...newFiles]);
        setMediaPreviews((prev) => [...prev, ...newPreviews]);
    };

    // Handle drag and drop
    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        handleFileSelect(e.dataTransfer.files);
    };

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
    };

    // Remove media file
    const removeMedia = (index: number) => {
        setMediaFiles((prev) => prev.filter((_, i) => i !== index));
        setMediaPreviews((prev) => prev.filter((_, i) => i !== index));
        setUploadedMediaUrls((prev) => prev.filter((_, i) => i !== index));
    };

    const handleSubmit = async () => {
        if (postType === "link") {
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
                    post_type: "link",
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
        } else {
            // Media post
            if (mediaFiles.length === 0) {
                toast.error("Selecteer minimaal één afbeelding of video");
                return;
            }

            setIsSubmitting(true);
            setIsUploading(true);

            try {
                // Upload all media files
                const uploadPromises = mediaFiles.map((file) => uploadMedia(file));
                const uploadResults = await Promise.all(uploadPromises);
                const mediaUrls = uploadResults.map((result) => result.url);

                // Create media post (use first media URL as placeholder URL)
                await createSharedLink({
                    url: mediaUrls[0] || "", // Required field, but not used for media posts
                    post_type: "media",
                    media_urls: mediaUrls,
                });

                toast.success("Media gedeeld!");
                onOpenChange(false);
                onSuccess?.();
            } catch (err: any) {
                toast.error("Kon media niet delen", {
                    description: err.message || "Er is een fout opgetreden",
                });
            } finally {
                setIsSubmitting(false);
                setIsUploading(false);
            }
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Deel op Prikbord</DialogTitle>
                    <DialogDescription>
                        Deel een link of upload afbeeldingen en video's
                    </DialogDescription>
                </DialogHeader>

                <Tabs value={postType} onValueChange={(v) => setPostType(v as "link" | "media")} className="w-full">
                    <TabsList className="grid w-full grid-cols-2">
                        <TabsTrigger value="link">Link</TabsTrigger>
                        <TabsTrigger value="media">Media</TabsTrigger>
                    </TabsList>

                    <TabsContent value="link" className="space-y-4 mt-4">
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
                    </TabsContent>

                    <TabsContent value="media" className="space-y-4 mt-4">
                        <div className="space-y-2">
                            <Label>Afbeeldingen of video's</Label>
                            <div
                                className={cn(
                                    "border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors",
                                    "hover:border-primary/50 hover:bg-muted/50",
                                    isSubmitting && "opacity-50 cursor-not-allowed"
                                )}
                                onDrop={handleDrop}
                                onDragOver={handleDragOver}
                                onClick={() => !isSubmitting && fileInputRef.current?.click()}
                            >
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    multiple
                                    accept="image/*,video/*"
                                    onChange={(e) => handleFileSelect(e.target.files)}
                                    className="hidden"
                                    disabled={isSubmitting}
                                />
                                <Icon name="Upload" className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                                <p className="text-sm text-muted-foreground mb-1">
                                    Sleep bestanden hierheen of klik om te selecteren
                                </p>
                                <p className="text-xs text-muted-foreground">
                                    Afbeeldingen (max 5MB) of video's (max 50MB)
                                </p>
                            </div>
                        </div>

                        {mediaPreviews.length > 0 && (
                            <div className="space-y-2">
                                <Label>Preview ({mediaPreviews.length})</Label>
                                <div className="grid grid-cols-2 gap-2">
                                    {mediaPreviews.map((preview, index) => {
                                        const file = mediaFiles[index];
                                        const isVideo = file?.type.startsWith("video/");
                                        return (
                                            <div key={index} className="relative group">
                                                {isVideo ? (
                                                    <video
                                                        src={preview}
                                                        className="w-full h-32 object-cover rounded-lg"
                                                        controls={false}
                                                    />
                                                ) : (
                                                    <img
                                                        src={preview}
                                                        alt={`Preview ${index + 1}`}
                                                        className="w-full h-32 object-cover rounded-lg"
                                                    />
                                                )}
                                                <button
                                                    type="button"
                                                    onClick={() => removeMedia(index)}
                                                    className="absolute top-1 right-1 bg-destructive text-destructive-foreground rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                                                    disabled={isSubmitting}
                                                >
                                                    <Icon name="X" className="h-3 w-3" />
                                                </button>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        )}
                    </TabsContent>
                </Tabs>

                <DialogFooter>
                    <Button
                        variant="outline"
                        onClick={() => onOpenChange(false)}
                        disabled={isSubmitting}
                    >
                        Annuleren
                    </Button>
                    <Button
                        onClick={handleSubmit}
                        disabled={
                            isSubmitting ||
                            (postType === "link" && !url.trim()) ||
                            (postType === "media" && mediaFiles.length === 0)
                        }
                    >
                        {isSubmitting || isUploading ? (
                            <>
                                <Icon name="Loader2" className="h-4 w-4 mr-2 animate-spin" />
                                {isUploading ? "Uploaden..." : "Delen..."}
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

