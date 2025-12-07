// Frontend/src/components/bulletin/BulletinPostDetail.tsx
import { Icon } from "@/components/Icon";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { useAuth } from "@/hooks/useAuth";
import { deleteBulletinPost, trackContactClick } from "@/lib/api/bulletin";
import type { BulletinPost } from "@/types/bulletin";
import { format } from "date-fns";
import { nl } from "date-fns/locale";
import { useState } from "react";
import { toast } from "sonner";

interface BulletinPostDetailProps {
    post: BulletinPost | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onDelete?: () => void;
}

const categoryLabels: Record<BulletinPost["category"], string> = {
    personnel_wanted: "Personeel gezocht",
    offer: "Aanbieding",
    free_for_sale: "Gratis/Te koop",
    event: "Evenement",
    services: "Diensten",
    other: "Overig",
};

export function BulletinPostDetail({
    post,
    open,
    onOpenChange,
    onDelete,
}: BulletinPostDetailProps) {
    const { isAuthenticated } = useAuth();
    const [showContact, setShowContact] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);

    const handleContactClick = async () => {
        if (!showContact && post) {
            setShowContact(true);
            try {
                await trackContactClick(post.id);
            } catch (err) {
                console.error("Failed to track contact click:", err);
            }
        }
    };

    const handleDelete = async () => {
        if (!post) return;

        if (!confirm("Weet je zeker dat je deze advertentie wilt verwijderen?")) {
            return;
        }

        setIsDeleting(true);
        try {
            await deleteBulletinPost(post.id);
            toast.success("Advertentie verwijderd");
            onOpenChange(false);
            onDelete?.();
        } catch (err: any) {
            toast.error("Kon advertentie niet verwijderen", {
                description: err.message || "Er is een fout opgetreden",
            });
        } finally {
            setIsDeleting(false);
        }
    };

    const formatDate = (dateStr: string) => {
        try {
            return format(new Date(dateStr), "d MMMM yyyy 'om' HH:mm", { locale: nl });
        } catch {
            return dateStr;
        }
    };

    const daysUntilExpiry = post?.expires_at
        ? Math.ceil((new Date(post.expires_at).getTime() - Date.now()) / (1000 * 60 * 60 * 24))
        : null;

    // Check if user can delete (simplified - should check actual ownership)
    const canDelete = isAuthenticated && post; // Only allow delete if authenticated and post exists

    return (
        <Dialog open={open && !!post} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                {post ? (
                    <>
                        <DialogHeader>
                            <div className="flex items-start justify-between gap-2">
                                <DialogTitle className="text-2xl">{post.title}</DialogTitle>
                                {canDelete && (
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={handleDelete}
                                        disabled={isDeleting}
                                        className="text-destructive hover:text-destructive"
                                    >
                                        <Icon name="Trash2" className="h-4 w-4" />
                                    </Button>
                                )}
                            </div>
                        </DialogHeader>

                        <div className="space-y-4">
                            {/* Meta info */}
                            <div className="flex items-center gap-2 flex-wrap">
                                <Badge variant="secondary">{categoryLabels[post.category]}</Badge>
                                {post.city && (
                                    <Badge variant="outline">
                                        <Icon name="MapPin" className="h-3 w-3 mr-1" />
                                        {post.city}
                                    </Badge>
                                )}
                                {post.neighborhood && (
                                    <Badge variant="outline" className="text-xs">
                                        {post.neighborhood}
                                    </Badge>
                                )}
                                {post.creator.verified && (
                                    <Badge variant="default" className="bg-blue-600">
                                        <Icon name="Check" className="h-3 w-3 mr-1" />
                                        Geverifieerd
                                    </Badge>
                                )}
                            </div>

                            {/* Creator info */}
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                <Icon name={post.creator.type === "business" ? "Building" : "User"} className="h-4 w-4" />
                                <span>
                                    {post.creator.name || `Gebruiker ${post.creator.id?.substring(0, 8) || ""}`}
                                    {post.creator.type === "business" && " (Bedrijf)"}
                                </span>
                            </div>

                            {/* Description */}
                            {post.description && (
                                <div className="prose prose-sm max-w-none">
                                    <p className="whitespace-pre-wrap">{post.description}</p>
                                </div>
                            )}

                            {/* Images */}
                            {post.image_urls && post.image_urls.length > 0 && (
                                <div className="grid grid-cols-2 gap-2">
                                    {post.image_urls.map((url, idx) => (
                                        <img
                                            key={idx}
                                            src={url}
                                            alt={`${post.title} - Afbeelding ${idx + 1}`}
                                            className="rounded-lg object-cover w-full h-48"
                                        />
                                    ))}
                                </div>
                            )}

                            {/* Linked location */}
                            {post.linked_location && (
                                <div className="p-3 bg-muted rounded-lg">
                                    <div className="flex items-center gap-2 text-sm font-medium">
                                        <Icon name="MapPin" className="h-4 w-4" />
                                        Gerelateerde locatie
                                    </div>
                                    <div className="mt-1 text-sm">
                                        <div className="font-medium">{post.linked_location.name}</div>
                                        {post.linked_location.address && (
                                            <div className="text-muted-foreground">{post.linked_location.address}</div>
                                        )}
                                    </div>
                                </div>
                            )}

                            {/* Contact info */}
                            {post.contact_info && showContact && (
                                <div className="p-4 border rounded-lg space-y-2">
                                    <h4 className="font-medium text-sm">Contactinformatie</h4>
                                    <div className="space-y-2 text-sm">
                                        {post.contact_info.phone && (
                                            <a
                                                href={`tel:${post.contact_info.phone}`}
                                                className="flex items-center gap-2 text-blue-600 hover:underline"
                                            >
                                                <Icon name="Phone" className="h-4 w-4" />
                                                {post.contact_info.phone}
                                            </a>
                                        )}
                                        {post.contact_info.email && (
                                            <a
                                                href={`mailto:${post.contact_info.email}`}
                                                className="flex items-center gap-2 text-blue-600 hover:underline"
                                            >
                                                <Icon name="Mail" className="h-4 w-4" />
                                                {post.contact_info.email}
                                            </a>
                                        )}
                                        {post.contact_info.whatsapp && (
                                            <a
                                                href={`https://wa.me/${post.contact_info.whatsapp.replace(/[^0-9]/g, "")}`}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="flex items-center gap-2 text-green-600 hover:underline"
                                            >
                                                <Icon name="MessageCircle" className="h-4 w-4" />
                                                WhatsApp: {post.contact_info.whatsapp}
                                            </a>
                                        )}
                                    </div>
                                </div>
                            )}

                            {post.contact_info && !showContact && (
                                <Button onClick={handleContactClick} variant="outline" className="w-full">
                                    <Icon name="Eye" className="h-4 w-4 mr-2" />
                                    Toon contactinformatie
                                </Button>
                            )}

                            {/* Stats */}
                            <div className="flex items-center gap-4 text-sm text-muted-foreground pt-2 border-t">
                                <span className="flex items-center gap-1">
                                    <Icon name="Eye" className="h-4 w-4" />
                                    {post.view_count} {post.view_count === 1 ? "weergave" : "weergaven"}
                                </span>
                                {post.contact_count > 0 && (
                                    <span className="flex items-center gap-1">
                                        <Icon name="Phone" className="h-4 w-4" />
                                        {post.contact_count} {post.contact_count === 1 ? "contact" : "contacten"}
                                    </span>
                                )}
                            </div>

                            {/* Dates */}
                            <div className="text-xs text-muted-foreground space-y-1 pt-2 border-t">
                                <div>Geplaatst op {formatDate(post.created_at)}</div>
                                {post.expires_at && (
                                    <div>
                                        {daysUntilExpiry !== null && daysUntilExpiry > 0 ? (
                                            <span className="text-green-600">
                                                Geldig t/m {formatDate(post.expires_at)} ({daysUntilExpiry} {daysUntilExpiry === 1 ? "dag" : "dagen"})
                                            </span>
                                        ) : (
                                            <span className="text-red-600">Verlopen</span>
                                        )}
                                    </div>
                                )}
                            </div>

                            {/* Moderation status (if not active) */}
                            {post.moderation_status !== "approved" && post.status !== "active" && (
                                <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm">
                                    <div className="flex items-center gap-2 text-yellow-800">
                                        <Icon name="AlertCircle" className="h-4 w-4" />
                                        <span className="font-medium">
                                            {post.moderation_status === "pending" && "In afwachting van goedkeuring"}
                                            {post.moderation_status === "requires_review" && "In afwachting van beoordeling"}
                                            {post.moderation_status === "rejected" && "Afgewezen"}
                                            {post.status === "expired" && "Verlopen"}
                                            {post.status === "removed" && "Verwijderd"}
                                        </span>
                                    </div>
                                    {post.moderation_message && (
                                        <div className="mt-1 text-yellow-700">{post.moderation_message}</div>
                                    )}
                                </div>
                            )}
                        </div>
                    </>
                ) : (
                    <DialogHeader>
                        <DialogTitle>Laden...</DialogTitle>
                    </DialogHeader>
                )}
            </DialogContent>
        </Dialog>
    );
}
