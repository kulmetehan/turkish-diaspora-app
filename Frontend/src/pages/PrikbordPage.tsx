// Frontend/src/pages/PrikbordPage.tsx
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/Icon";
import { PrikbordFeed } from "@/components/prikbord/PrikbordFeed";
import { ShareLinkDialog } from "@/components/prikbord/ShareLinkDialog";
import type { SharedLink } from "@/types/prikbord";
import { PageShell } from "@/components/layout/PageShell";
import { SeoHead } from "@/lib/seo/SeoHead";
import { useSeo } from "@/lib/seo/useSeo";
import { useTranslation } from "@/hooks/useTranslation";

export default function PrikbordPage() {
  const { t } = useTranslation();
  const seo = useSeo();
  const [isShareDialogOpen, setIsShareDialogOpen] = useState(false);

  const handleLinkClick = (link: SharedLink) => {
    // Open link in new tab (only for link posts, not media/text)
    if (link.post_type === "link") {
      window.open(link.url, "_blank", "noopener,noreferrer");
    }
  };

  const handleShareSuccess = () => {
    // Feed will update optimistically via PrikbordFeed
    // No need to refresh manually
  };

  return (
    <>
      <SeoHead {...seo} />
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
            {t("prikbord.share.shareLink")}
          </Button>
        </div>

        <PrikbordFeed
          onLinkClick={handleLinkClick}
        />

        <ShareLinkDialog
          open={isShareDialogOpen}
          onOpenChange={setIsShareDialogOpen}
          onSuccess={handleShareSuccess}
        />
      </div>
    </PageShell>
    </>
  );
}

