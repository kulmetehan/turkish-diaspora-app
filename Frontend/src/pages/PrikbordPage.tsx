// Frontend/src/pages/PrikbordPage.tsx
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/Icon";
import { PrikbordFeed } from "@/components/prikbord/PrikbordFeed";
import { ShareLinkDialog } from "@/components/prikbord/ShareLinkDialog";
import type { SharedLink } from "@/types/prikbord";
import { PageShell } from "@/components/layout/PageShell";

export default function PrikbordPage() {
  const [isShareDialogOpen, setIsShareDialogOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleLinkClick = (link: SharedLink) => {
    // Open link in new tab
    window.open(link.url, "_blank", "noopener,noreferrer");
  };

  const handleShareSuccess = () => {
    // Refresh feed
    setRefreshKey((prev) => prev + 1);
  };

  return (
    <PageShell
      title="Prikbord"
      subtitle="Ontdek wat de community deelt — zonder ruis, zonder discussies."
    >
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Prikbord</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Deel links van Marktplaats, Instagram, YouTube en meer
            </p>
          </div>
          <Button
            onClick={() => setIsShareDialogOpen(true)}
            className="gap-2"
          >
            <Icon name="Plus" className="h-4 w-4" />
            Deel link
          </Button>
        </div>

        <PrikbordFeed
          key={refreshKey}
          onLinkClick={handleLinkClick}
        />

        <ShareLinkDialog
          open={isShareDialogOpen}
          onOpenChange={setIsShareDialogOpen}
          onSuccess={handleShareSuccess}
        />
      </div>
    </PageShell>
  );
}

