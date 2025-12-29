import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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
import { Icon } from "@/components/Icon";
import {
  getLocationSubmission,
  approveLocationSubmission,
  rejectLocationSubmission,
  type LocationSubmissionResponse,
} from "@/lib/apiAdmin";
import { format } from "date-fns";
import { nl } from "date-fns/locale";

export default function AdminLocationSubmissionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [submission, setSubmission] = useState<LocationSubmissionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [rejectDialogOpen, setRejectDialogOpen] = useState(false);
  const [rejectionReason, setRejectionReason] = useState("");
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    if (!id) return;
    loadSubmission();
  }, [id]);

  const loadSubmission = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await getLocationSubmission(Number(id));
      setSubmission(data);
    } catch (err: any) {
      toast.error("Kon inzending niet laden", { description: err.message });
      navigate("/admin/location-submissions");
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async () => {
    if (!id) return;
    setProcessing(true);
    try {
      await approveLocationSubmission(Number(id));
      toast.success("Inzending goedgekeurd");
      await loadSubmission();
    } catch (err: any) {
      toast.error("Kon inzending niet goedkeuren", { description: err.message });
    } finally {
      setProcessing(false);
    }
  };

  const handleReject = async () => {
    if (!id) return;
    setProcessing(true);
    try {
      await rejectLocationSubmission(Number(id), rejectionReason.trim() || undefined);
      toast.success("Inzending afgewezen");
      setRejectDialogOpen(false);
      setRejectionReason("");
      await loadSubmission();
    } catch (err: any) {
      toast.error("Kon inzending niet afwijzen", { description: err.message });
    } finally {
      setProcessing(false);
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          <p className="mt-4 text-muted-foreground">Laden...</p>
        </div>
      </div>
    );
  }

  if (!submission) {
    return (
      <div className="container mx-auto p-6">
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            Inzending niet gevonden.
          </CardContent>
        </Card>
      </div>
    );
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "pending":
        return <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-300">In behandeling</Badge>;
      case "approved":
        return <Badge variant="outline" className="bg-green-50 text-green-700 border-green-300">Goedgekeurd</Badge>;
      case "rejected":
        return <Badge variant="outline" className="bg-red-50 text-red-700 border-red-300">Afgewezen</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" onClick={() => navigate("/admin/location-submissions")}>
          <Icon name="ArrowLeft" sizeRem={1} className="mr-2" />
          Terug
        </Button>
        <h1 className="text-3xl font-bold">Locatie Inzending Details</h1>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <CardTitle className="text-2xl">{submission.name}</CardTitle>
              <p className="text-sm text-muted-foreground mt-2">
                Ingediend op {format(new Date(submission.submitted_at), "d MMM yyyy 'om' HH:mm", { locale: nl })}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {getStatusBadge(submission.status)}
              {submission.is_owner && (
                <Badge variant="secondary" className="bg-blue-50 text-blue-700 border-blue-300">
                  Eigenaar
                </Badge>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label className="text-muted-foreground">Categorie</Label>
              <p className="font-medium">{submission.category}</p>
            </div>
            <div>
              <Label className="text-muted-foreground">Coördinaten</Label>
              <p className="font-medium">{submission.lat.toFixed(6)}, {submission.lng.toFixed(6)}</p>
            </div>
            {submission.address && (
              <div className="md:col-span-2">
                <Label className="text-muted-foreground">Adres</Label>
                <p className="font-medium">{submission.address}</p>
              </div>
            )}
            {submission.created_location_id && (
              <div>
                <Label className="text-muted-foreground">Aangemaakte Locatie ID</Label>
                <p className="font-medium text-green-600">{submission.created_location_id}</p>
              </div>
            )}
            {submission.reviewed_at && (
              <div>
                <Label className="text-muted-foreground">Beoordeeld op</Label>
                <p className="font-medium">
                  {format(new Date(submission.reviewed_at), "d MMM yyyy 'om' HH:mm", { locale: nl })}
                </p>
              </div>
            )}
            {submission.rejection_reason && (
              <div className="md:col-span-2">
                <Label className="text-muted-foreground">Afwijzingsreden</Label>
                <p className="font-medium text-red-600">{submission.rejection_reason}</p>
              </div>
            )}
          </div>

          {/* Map preview would go here - for now just show coordinates */}
          <div className="mt-6 p-4 bg-muted rounded-lg">
            <p className="text-sm text-muted-foreground">
              Kaart preview zou hier komen. Coördinaten: {submission.lat.toFixed(6)}, {submission.lng.toFixed(6)}
            </p>
          </div>

          {submission.status === "pending" && (
            <div className="flex gap-4 pt-4 border-t">
              <Button
                onClick={handleApprove}
                disabled={processing}
                className="bg-green-600 hover:bg-green-700"
              >
                {processing ? "Bezig..." : "Goedkeuren"}
              </Button>
              <Button
                variant="destructive"
                onClick={() => setRejectDialogOpen(true)}
                disabled={processing}
              >
                Afwijzen
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Reject Dialog */}
      <Dialog open={rejectDialogOpen} onOpenChange={setRejectDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Inzending afwijzen</DialogTitle>
            <DialogDescription>
              Geef een reden op voor het afwijzen van deze inzending (optioneel).
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="rejection-reason">Reden (optioneel)</Label>
              <Textarea
                id="rejection-reason"
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                placeholder="Bijv. Locatie bestaat al, onjuiste informatie, etc."
                rows={4}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRejectDialogOpen(false)} disabled={processing}>
              Annuleren
            </Button>
            <Button variant="destructive" onClick={handleReject} disabled={processing}>
              {processing ? "Bezig..." : "Afwijzen"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}



