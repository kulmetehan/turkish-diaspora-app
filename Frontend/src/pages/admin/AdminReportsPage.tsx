import { useState, useEffect } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Icon } from "@/components/Icon";
import {
  listAdminReports,
  updateAdminReport,
  removeReportedContent,
  type AdminReport,
  type AdminReportUpdateRequest,
} from "@/lib/apiAdmin";
import { format } from "date-fns";
import { nl } from "date-fns/locale";

export default function AdminReportsPage() {
  const [reports, setReports] = useState<AdminReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [selectedReport, setSelectedReport] = useState<AdminReport | null>(null);
  const [updateDialogOpen, setUpdateDialogOpen] = useState(false);
  const [newStatus, setNewStatus] = useState<"pending" | "resolved" | "dismissed">("pending");
  const [resolutionNotes, setResolutionNotes] = useState<string>("");
  const [updating, setUpdating] = useState(false);
  const [removeConfirmOpen, setRemoveConfirmOpen] = useState(false);
  const [reportToRemove, setReportToRemove] = useState<number | null>(null);
  const [removing, setRemoving] = useState(false);

  const loadReports = async () => {
    setLoading(true);
    try {
      const data = await listAdminReports({
        status: statusFilter !== "all" ? (statusFilter as any) : undefined,
        report_type: typeFilter !== "all" ? (typeFilter as any) : undefined,
        limit: 200,
      });
      setReports(data);
    } catch (err: any) {
      toast.error("Kon reports niet laden", { description: err.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReports();
  }, [statusFilter, typeFilter]);

  const handleUpdateClick = (report: AdminReport) => {
    setSelectedReport(report);
    setNewStatus(report.status);
    setResolutionNotes("");
    setUpdateDialogOpen(true);
  };

  const handleUpdate = async () => {
    if (!selectedReport) return;

    setUpdating(true);
    try {
      const update: AdminReportUpdateRequest = {
        status: newStatus,
        resolution_notes: resolutionNotes.trim() || null,
      };
      await updateAdminReport(selectedReport.id, update);
      toast.success("Report status bijgewerkt");
      setUpdateDialogOpen(false);
      setSelectedReport(null);
      await loadReports();
    } catch (err: any) {
      toast.error("Kon report niet bijwerken", { description: err.message });
    } finally {
      setUpdating(false);
    }
  };

  const handleRemoveClick = (reportId: number) => {
    setReportToRemove(reportId);
    setRemoveConfirmOpen(true);
  };

  const confirmRemove = async () => {
    if (reportToRemove === null) return;

    setRemoving(true);
    try {
      await removeReportedContent(reportToRemove);
      toast.success("Content verwijderd en report opgelost");
      setRemoveConfirmOpen(false);
      setReportToRemove(null);
      await loadReports();
    } catch (err: any) {
      toast.error("Kon content niet verwijderen", { description: err.message });
    } finally {
      setRemoving(false);
    }
  };

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case "pending":
        return "default";
      case "resolved":
        return "default";
      case "dismissed":
        return "secondary";
      default:
        return "outline";
    }
  };

  const getTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      location: "Locatie",
      note: "Notitie",
      reaction: "Reactie",
      user: "Gebruiker",
    };
    return labels[type] || type;
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Reports Beheer</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Beheer gebruikersrapportages over content en gebruikers
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
            <CardTitle>Reports ({reports.length})</CardTitle>
            <div className="flex gap-2">
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Alle statussen</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="resolved">Resolved</SelectItem>
                  <SelectItem value="dismissed">Dismissed</SelectItem>
                </SelectContent>
              </Select>
              <Select value={typeFilter} onValueChange={setTypeFilter}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="Type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Alle types</SelectItem>
                  <SelectItem value="location">Locatie</SelectItem>
                  <SelectItem value="note">Notitie</SelectItem>
                  <SelectItem value="reaction">Reactie</SelectItem>
                  <SelectItem value="user">Gebruiker</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-muted-foreground">Reports laden...</p>
          ) : reports.length === 0 ? (
            <p className="text-muted-foreground">Geen reports gevonden.</p>
          ) : (
            <div className="space-y-4">
              {reports.map((report) => (
                <Card key={report.id} className="rounded-xl">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 space-y-2">
                        <div className="flex items-center gap-2">
                          <Badge variant={getStatusBadgeVariant(report.status)}>
                            {report.status}
                          </Badge>
                          <Badge variant="outline">{getTypeLabel(report.report_type)}</Badge>
                        </div>
                        <div>
                          <p className="text-sm font-medium">
                            Reden: {report.reason}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            Target ID: {report.target_id} ({report.report_type})
                          </p>
                          {report.details && (
                            <p className="text-sm text-muted-foreground mt-1">
                              {report.details}
                            </p>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {format(new Date(report.created_at), "dd-MM-yyyy HH:mm", { locale: nl })}
                        </p>
                      </div>
                      <div className="flex gap-2">
                        {(report.report_type === "note" || report.report_type === "reaction") && report.status === "pending" && (
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => handleRemoveClick(report.id)}
                          >
                            <Icon name="Trash2" sizeRem={1} className="mr-2" />
                            Verwijder
                          </Button>
                        )}
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleUpdateClick(report)}
                        >
                          <Icon name="Edit" sizeRem={1} className="mr-2" />
                          Update
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={updateDialogOpen} onOpenChange={setUpdateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Update Report Status</DialogTitle>
            <DialogDescription>
              Update de status van report #{selectedReport?.id}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="status">Status</Label>
              <Select value={newStatus} onValueChange={(v) => setNewStatus(v as any)}>
                <SelectTrigger id="status">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="resolved">Resolved</SelectItem>
                  <SelectItem value="dismissed">Dismissed</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="notes">Resolution Notes (optioneel)</Label>
              <Textarea
                id="notes"
                placeholder="Notities over de resolutie..."
                value={resolutionNotes}
                onChange={(e) => setResolutionNotes(e.target.value)}
                rows={4}
                maxLength={1000}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setUpdateDialogOpen(false)}>
              Annuleren
            </Button>
            <Button onClick={handleUpdate} disabled={updating}>
              {updating ? "Bijwerken..." : "Bijwerken"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={removeConfirmOpen} onOpenChange={setRemoveConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Content Verwijderen</DialogTitle>
            <DialogDescription>
              Weet je zeker dat je deze content wilt verwijderen? Deze actie kan niet ongedaan worden gemaakt.
              Het report zal automatisch als "resolved" gemarkeerd worden.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRemoveConfirmOpen(false)} disabled={removing}>
              Annuleren
            </Button>
            <Button variant="destructive" onClick={confirmRemove} disabled={removing}>
              {removing ? "Verwijderen..." : "Verwijderen"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

