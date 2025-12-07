// Frontend/src/components/bulletin/BulletinPostCard.tsx
import { useState } from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Icon } from "@/components/Icon";
import { cn } from "@/lib/ui/cn";
import type { BulletinPost } from "@/types/bulletin";
import { format } from "date-fns";
import { nl } from "date-fns/locale";
import { trackContactClick, reportBulletinPost } from "@/lib/api/bulletin";
import { toast } from "sonner";

interface BulletinPostCardProps {
  post: BulletinPost;
  onDetailClick?: () => void;
  onDelete?: () => void;
  className?: string;
  showDelete?: boolean;
}

const categoryLabels: Record<BulletinPost["category"], string> = {
  personnel_wanted: "Personeel gezocht",
  offer: "Aanbieding",
  free_for_sale: "Gratis/Te koop",
  event: "Evenement",
  services: "Diensten",
  other: "Overig",
};

export function BulletinPostCard({
  post,
  onDetailClick,
  onDelete,
  className,
  showDelete = false,
}: BulletinPostCardProps) {
  const [showContact, setShowContact] = useState(false);
  const [isTrackingContact, setIsTrackingContact] = useState(false);

  const handleContactClick = async () => {
    if (!showContact) {
      setShowContact(true);
      
      // Track contact click
      try {
        setIsTrackingContact(true);
        await trackContactClick(post.id);
      } catch (err) {
        console.error("Failed to track contact click:", err);
      } finally {
        setIsTrackingContact(false);
      }
    }
  };

  const handleReport = async () => {
    if (!confirm("Weet je zeker dat je deze advertentie wilt rapporteren?")) {
      return;
    }

    try {
      await reportBulletinPost(post.id, "inappropriate", "Reported by user");
      toast.success("Rapportage verzonden");
    } catch (err: any) {
      toast.error("Kon rapportage niet verzenden", {
        description: err.message || "Er is een fout opgetreden",
      });
    }
  };

  const formatDate = (dateStr: string) => {
    try {
      return format(new Date(dateStr), "d MMM yyyy", { locale: nl });
    } catch {
      return dateStr;
    }
  };

  const daysUntilExpiry = post.expires_at
    ? Math.ceil((new Date(post.expires_at).getTime() - Date.now()) / (1000 * 60 * 60 * 24))
    : null;

  return (
    <Card
      className={cn(
        "rounded-xl border border-border/80 bg-card shadow-soft transition-all duration-200",
        "hover:border-border hover:shadow-card",
        className
      )}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1">
            <h3
              className="text-lg font-semibold mb-1 cursor-pointer hover:text-primary transition-colors"
              onClick={onDetailClick}
            >
              {post.title}
            </h3>
            <div className="flex items-center gap-2 flex-wrap">
              <Badge variant="secondary" className="text-xs">
                {categoryLabels[post.category]}
              </Badge>
              {post.city && (
                <span className="text-xs text-muted-foreground">{post.city}</span>
              )}
              {post.creator.verified && (
                <Badge variant="outline" className="text-xs">
                  <Icon name="CheckCircle" className="h-3 w-3 mr-1" />
                  Geverifieerd
                </Badge>
              )}
            </div>
          </div>
          {showDelete && (
            <Button
              variant="ghost"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                onDelete?.();
              }}
              className="text-destructive hover:text-destructive"
            >
              <Icon name="Trash2" className="h-4 w-4" />
            </Button>
          )}
        </div>
        <div className="flex items-center gap-3 text-xs text-muted-foreground mt-2">
          <span>Door {post.creator.name || "Onbekend"}</span>
          <span>•</span>
          <span>{formatDate(post.created_at)}</span>
          {daysUntilExpiry !== null && daysUntilExpiry > 0 && (
            <>
              <span>•</span>
              <span>Geldig t/m {format(new Date(post.expires_at!), "d MMM", { locale: nl })}</span>
            </>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {post.description && (
          <p className="text-sm text-muted-foreground line-clamp-2">{post.description}</p>
        )}
        
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <Icon name="Eye" className="h-3 w-3" />
              {post.view_count}
            </span>
            {post.contact_count > 0 && (
              <span className="flex items-center gap-1">
                <Icon name="Phone" className="h-3 w-3" />
                {post.contact_count} contacten
              </span>
            )}
          </div>
          
          <div className="flex items-center gap-2">
            {post.contact_info && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleContactClick}
                disabled={isTrackingContact}
                className="text-xs"
              >
                <Icon name="Phone" className="h-3 w-3 mr-1" />
                Contact
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={handleReport}
              className="text-xs text-muted-foreground"
            >
              <Icon name="Flag" className="h-3 w-3" />
            </Button>
          </div>
        </div>

        {showContact && post.contact_info && (
          <div className="pt-3 border-t border-border space-y-2">
            <p className="text-xs font-semibold text-muted-foreground">Contactinformatie:</p>
            {post.contact_info.phone && (
              <a
                href={`tel:${post.contact_info.phone}`}
                className="block text-sm text-primary hover:underline"
              >
                <Icon name="Phone" className="h-3 w-3 inline mr-1" />
                {post.contact_info.phone}
              </a>
            )}
            {post.contact_info.email && (
              <a
                href={`mailto:${post.contact_info.email}`}
                className="block text-sm text-primary hover:underline"
              >
                <Icon name="Mail" className="h-3 w-3 inline mr-1" />
                {post.contact_info.email}
              </a>
            )}
            {post.contact_info.whatsapp && (
              <a
                href={`https://wa.me/${post.contact_info.whatsapp.replace(/[^\d]/g, "")}`}
                target="_blank"
                rel="noopener noreferrer"
                className="block text-sm text-primary hover:underline"
              >
                <Icon name="MessageCircle" className="h-3 w-3 inline mr-1" />
                WhatsApp: {post.contact_info.whatsapp}
              </a>
            )}
          </div>
        )}

        {onDetailClick && (
          <Button
            variant="ghost"
            size="sm"
            className="w-full text-xs"
            onClick={onDetailClick}
          >
            Bekijk details
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

