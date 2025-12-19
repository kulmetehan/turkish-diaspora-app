import { useState } from "react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { submitReport, type ReportCreateRequest } from "@/lib/api";

interface ReportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  reportType: "location" | "note" | "reaction" | "user";
  targetId: number;
  targetName?: string; // Optional name for display
}

const REPORT_REASONS: Record<string, string[]> = {
  location: ["Spam", "Incorrect Information", "Inappropriate Content", "Duplicate", "Other"],
  note: ["Spam", "Inappropriate Content", "Harassment", "False Information", "Other"],
  reaction: ["Spam", "Inappropriate", "Harassment", "Other"],
  user: ["Spam", "Harassment", "Impersonation", "Inappropriate Behavior", "Other"],
};

export function ReportDialog({
  open,
  onOpenChange,
  reportType,
  targetId,
  targetName,
}: ReportDialogProps) {
  const [reason, setReason] = useState<string>("");
  const [details, setDetails] = useState<string>("");
  const [loading, setLoading] = useState(false);

  const reasons = REPORT_REASONS[reportType] || REPORT_REASONS.location;
  const typeLabels: Record<string, string> = {
    location: "Locatie",
    note: "Notitie",
    reaction: "Reactie",
    user: "Gebruiker",
  };

  const handleSubmit = async () => {
    if (!reason.trim()) {
      toast.error("Selecteer een reden");
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
      toast.success("Melding verzonden. Bedankt voor je feedback!");
      onOpenChange(false);
      // Reset form
      setReason("");
      setDetails("");
    } catch (error: any) {
      if (error.message?.includes("409") || error.message?.includes("already")) {
        toast.error("Je hebt deze melding al eerder ingediend");
      } else {
        toast.error("Kon melding niet verzenden", {
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
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Rapporteer {typeLabels[reportType]}</DialogTitle>
          <DialogDescription>
            {targetName && (
              <span className="block mb-2">
                Je rapporteert: <strong>{targetName}</strong>
              </span>
            )}
            Help ons om de community veilig en respectvol te houden door problematische inhoud te melden.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="reason">Reden *</Label>
            <Select value={reason} onValueChange={setReason}>
              <SelectTrigger id="reason">
                <SelectValue placeholder="Selecteer een reden" />
              </SelectTrigger>
              <SelectContent>
                {reasons.map((r) => (
                  <SelectItem key={r} value={r}>
                    {r}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="details">Extra details (optioneel)</Label>
            <Textarea
              id="details"
              placeholder="Beschrijf het probleem in detail..."
              value={details}
              onChange={(e) => setDetails(e.target.value)}
              rows={4}
              maxLength={1000}
            />
            <p className="text-xs text-muted-foreground">
              {details.length}/1000 tekens
            </p>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={loading}>
            Annuleren
          </Button>
          <Button onClick={handleSubmit} disabled={loading || !reason}>
            {loading ? "Verzenden..." : "Verzenden"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}




















