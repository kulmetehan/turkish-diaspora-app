import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/Icon";
import { ReportDialog } from "./ReportDialog";
import { cn } from "@/lib/ui/cn";

interface ReportButtonProps {
  reportType: "location" | "note" | "reaction" | "user";
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
  const [dialogOpen, setDialogOpen] = useState(false);

  const typeLabels: Record<string, string> = {
    location: "locatie",
    note: "notitie",
    reaction: "reactie",
    user: "gebruiker",
  };

  return (
    <>
      <Button
        variant={variant}
        size={size}
        onClick={() => setDialogOpen(true)}
        className={cn("text-muted-foreground hover:text-foreground", className)}
        aria-label={`Rapporteer ${typeLabels[reportType]}`}
      >
        <Icon name="Flag" sizeRem={size === "icon" ? 1 : 0.875} className="mr-1.5" />
        {size !== "icon" && "Rapporteer"}
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








