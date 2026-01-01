import { useState } from "react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { submitReport, type ReportCreateRequest } from "@/lib/api";
import { useTranslation } from "@/hooks/useTranslation";

interface ReportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  reportType: "location" | "note" | "reaction" | "user" | "check_in" | "prikbord_post" | "poll";
  targetId: number;
  targetName?: string; // Optional name for display
}

export function ReportDialog({
  open,
  onOpenChange,
  reportType,
  targetId,
  targetName,
}: ReportDialogProps) {
  const { t } = useTranslation();
  const [reason, setReason] = useState<string>("");
  const [details, setDetails] = useState<string>("");
  const [loading, setLoading] = useState(false);

  // Map report types to their reason keys
  const getReportReasons = (type: string): string[] => {
    if (type === "location") {
      return [
        t("report.reasons.noTurkishAffinity"),
        t("report.reasons.permanentlyClosed"),
        t("report.reasons.fakeSpam"),
        t("report.reasons.other"),
      ];
    } else if (type === "note") {
      return [
        t("report.reasons.spam"),
        t("report.reasons.inappropriateContent"),
        t("report.reasons.harassment"),
        t("report.reasons.falseInformation"),
        t("report.reasons.other"),
      ];
    } else if (type === "reaction") {
      return [
        t("report.reasons.spam"),
        t("report.reasons.inappropriate"),
        t("report.reasons.harassment"),
        t("report.reasons.other"),
      ];
    } else if (type === "user") {
      return [
        t("report.reasons.spam"),
        t("report.reasons.harassment"),
        t("report.reasons.impersonation"),
        t("report.reasons.inappropriateBehavior"),
        t("report.reasons.other"),
      ];
    }
    // Default fallback
    return [
      t("report.reasons.noTurkishAffinity"),
      t("report.reasons.permanentlyClosed"),
      t("report.reasons.fakeSpam"),
      t("report.reasons.other"),
    ];
  };

  const reasons = getReportReasons(reportType);
  const typeLabels: Record<string, string> = {
    location: t("report.types.location"),
    note: t("report.types.note"),
    reaction: t("report.types.reaction"),
    user: t("report.types.user"),
    check_in: t("report.types.checkIn"),
    prikbord_post: t("report.types.prikbordPost"),
    poll: t("report.types.poll"),
  };

  const handleSubmit = async () => {
    if (!reason.trim()) {
      toast.error(t("report.errors.reasonRequired"));
      return;
    }

    setLoading(true);
    try {
      const report: ReportCreateRequest = {
        report_type: reportType,
        target_id: targetId,
        reason: reason,
        details: details.trim() || null,
      };

      await submitReport(report);
      toast.success(t("report.success"));
      onOpenChange(false);
      // Reset form
      setReason("");
      setDetails("");
    } catch (error: any) {
      if (error.message?.includes("409") || error.message?.includes("already")) {
        toast.error(t("report.errors.alreadyReported"));
      } else {
        toast.error(t("report.errors.submitFailed"), {
          description: error.message || "Probeer het later opnieuw",
        });
      }
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (!loading) {
      onOpenChange(false);
      setReason("");
      setDetails("");
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent 
        className="sm:max-w-[500px] z-[80]"
        overlayClassName="z-[79]"
      >
        <DialogHeader>
          <DialogTitle>{t("report.title").replace("{type}", typeLabels[reportType])}</DialogTitle>
          <DialogDescription>
            {targetName && (
              <span className="block mb-2">
                {t("report.reporting").replace("{name}", targetName)}
              </span>
            )}
            {t("report.description")}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="reason">{t("report.reason")}</Label>
            <Select value={reason} onValueChange={setReason}>
              <SelectTrigger id="reason">
                <SelectValue placeholder={t("report.selectReason")} />
              </SelectTrigger>
              <SelectContent className="z-[81]">
                {reasons.map((r) => (
                  <SelectItem key={r} value={r}>
                    {r}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="details">{t("report.details")}</Label>
            <Textarea
              id="details"
              placeholder={t("report.detailsPlaceholder")}
              value={details}
              onChange={(e) => setDetails(e.target.value)}
              rows={4}
              maxLength={1000}
            />
            <p className="text-xs text-muted-foreground">
              {t("report.characterCount").replace("{count}", details.length.toString())}
            </p>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={loading}>
            {t("common.buttons.cancel")}
          </Button>
          <Button onClick={handleSubmit} disabled={loading || !reason}>
            {loading ? t("report.submitting") : t("report.submit")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

























