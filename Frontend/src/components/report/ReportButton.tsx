import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/Icon";
import { ReportDialog } from "./ReportDialog";
import { cn } from "@/lib/ui/cn";
import { useTranslation } from "@/hooks/useTranslation";

interface ReportButtonProps {
  reportType: "location" | "note" | "reaction" | "user" | "check_in" | "prikbord_post" | "poll";
  targetId: number;
  targetName?: string;
  variant?: "default" | "outline" | "ghost" | "icon";
  size?: "sm" | "md" | "lg" | "icon";
  className?: string;
}

export function ReportButton({
  reportType,
  targetId,
  targetName,
  variant = "ghost",
  size = "sm",
  className,
}: ReportButtonProps) {
  const { t } = useTranslation();
  const [dialogOpen, setDialogOpen] = useState(false);

  const typeLabels: Record<string, string> = {
    location: t("report.types.location"),
    note: t("report.types.note"),
    reaction: t("report.types.reaction"),
    user: t("report.types.user"),
    check_in: t("report.types.checkIn"),
    prikbord_post: t("report.types.prikbordPost"),
    poll: t("report.types.poll"),
  };

  return (
    <>
      <Button
        variant={variant}
        size={size}
        onClick={() => setDialogOpen(true)}
        className={cn("text-muted-foreground hover:text-foreground", className)}
        aria-label={t("report.buttonAria").replace("{type}", typeLabels[reportType])}
      >
        <Icon name="Flag" sizeRem={size === "icon" ? 1 : 0.875} className="mr-1.5" />
        {size !== "icon" && t("report.button")}
      </Button>
      <ReportDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        reportType={reportType}
        targetId={targetId}
        targetName={targetName}
      />
    </>
  );
}

























