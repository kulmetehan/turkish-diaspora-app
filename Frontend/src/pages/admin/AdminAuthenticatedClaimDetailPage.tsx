import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Icon } from "@/components/Icon";
import {
  getAuthenticatedClaim,
  approveAuthenticatedClaim,
  rejectAuthenticatedClaim,
  unlinkAuthenticatedClaim,
  type AuthenticatedClaimResponse,
} from "@/lib/apiAdmin";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export default function AdminAuthenticatedClaimDetailPage() {
  const { claimId } = useParams<{ claimId: string }>();
  const navigate = useNavigate();
  const [claim, setClaim] = useState<AuthenticatedClaimResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [approving, setApproving] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const [unlinking, setUnlinking] = useState(false);
  const [rejectDialogOpen, setRejectDialogOpen] = useState(false);
  const [unlinkDialogOpen, setUnlinkDialogOpen] = useState(false);
  const [rejectionReason, setRejectionReason] = useState("");
  const [unlinkReason, setUnlinkReason] = useState("");

  const loadClaim = async () => {
    if (!claimId) return;
    setLoading(true);
    try {
      const data = await getAuthenticatedClaim(parseInt(claimId));
      setClaim(data);
    } catch (error: any) {
      toast.error(`Failed to load claim: ${error.message}`);
      navigate("/admin/authenticated-claims");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadClaim();
  }, [claimId]);

  const handleApprove = async () => {
    if (!claimId) return;
    setApproving(true);
    try {
      await approveAuthenticatedClaim(parseInt(claimId));
      toast.success("Claim approved successfully");
      navigate("/admin/authenticated-claims");
    } catch (error: any) {
      toast.error(`Failed to approve claim: ${error.message}`);
    } finally {
      setApproving(false);
    }
  };

  const handleReject = async () => {
    if (!claimId) return;
    setRejecting(true);
    try {
      await rejectAuthenticatedClaim(parseInt(claimId), rejectionReason || undefined);
      toast.success("Claim rejected");
      navigate("/admin/authenticated-claims");
    } catch (error: any) {
      toast.error(`Failed to reject claim: ${error.message}`);
    } finally {
      setRejecting(false);
      setRejectDialogOpen(false);
      setRejectionReason("");
    }
  };

  const handleUnlink = async () => {
    if (!claimId) return;
    setUnlinking(true);
    try {
      await unlinkAuthenticatedClaim(parseInt(claimId), unlinkReason || undefined);
      toast.success("Locatie losgekoppeld");
      navigate("/admin/authenticated-claims");
    } catch (error: any) {
      toast.error(`Failed to unlink claim: ${error.message}`);
    } finally {
      setUnlinking(false);
      setUnlinkDialogOpen(false);
      setUnlinkReason("");
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("nl-NL", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center py-8">
          <div className="text-muted-foreground">Loading claim details...</div>
        </div>
      </div>
    );
  }

  if (!claim) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center py-8">
          <div className="text-muted-foreground">Claim not found</div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Button variant="ghost" onClick={() => navigate("/admin/authenticated-claims")}>
            <Icon name="ArrowLeft" sizeRem={1} className="mr-2" />
            Back to Claims
          </Button>
          <h1 className="text-2xl font-semibold mt-4">
            Claim Review: {claim.location_name || `Location ${claim.location_id}`}
          </h1>
        </div>
        <Badge
          variant="outline"
          className={
            claim.status === "pending"
              ? "bg-yellow-50 text-yellow-700 border-yellow-200"
              : claim.status === "approved"
              ? "bg-green-50 text-green-700 border-green-200"
              : "bg-red-50 text-red-700 border-red-200"
          }
        >
          {claim.status.charAt(0).toUpperCase() + claim.status.slice(1)}
        </Badge>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Location Information */}
        <Card>
          <CardHeader>
            <CardTitle>Location Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div>
              <Label className="text-muted-foreground">Location Name</Label>
              <div className="font-medium">{claim.location_name || "N/A"}</div>
            </div>
            <div>
              <Label className="text-muted-foreground">Location ID</Label>
              <div className="font-medium">{claim.location_id}</div>
            </div>
          </CardContent>
        </Card>

        {/* User Information */}
        <Card>
          <CardHeader>
            <CardTitle>User Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div>
              <Label className="text-muted-foreground">Name</Label>
              <div className="font-medium">{claim.user_name || "N/A"}</div>
            </div>
            <div>
              <Label className="text-muted-foreground">Email</Label>
              <div className="font-medium">{claim.user_email || "N/A"}</div>
            </div>
            <div>
              <Label className="text-muted-foreground">User ID</Label>
              <div className="font-mono text-sm">{claim.user_id}</div>
            </div>
          </CardContent>
        </Card>

        {/* Claim Details */}
        <Card>
          <CardHeader>
            <CardTitle>Claim Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div>
              <Label className="text-muted-foreground">Submitted At</Label>
              <div>{formatDate(claim.submitted_at)}</div>
            </div>
            {claim.reviewed_at && (
              <div>
                <Label className="text-muted-foreground">Reviewed At</Label>
                <div>{formatDate(claim.reviewed_at)}</div>
              </div>
            )}
            {claim.rejection_reason && (
              <div>
                <Label className="text-muted-foreground">Rejection Reason</Label>
                <div className="text-red-600">{claim.rejection_reason}</div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Google Business Link */}
        {claim.google_business_link && (
          <Card>
            <CardHeader>
              <CardTitle>Google Business Link</CardTitle>
            </CardHeader>
            <CardContent>
              <a
                href={claim.google_business_link}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline flex items-center gap-2"
              >
                <span>View Google Business Profile</span>
                <Icon name="ExternalLink" sizeRem={1} />
              </a>
            </CardContent>
          </Card>
        )}

        {/* Logo */}
        {claim.logo_url && (
          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle>Logo</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4">
                <img
                  src={claim.logo_url}
                  alt="Location logo"
                  className="w-32 h-32 object-contain border rounded"
                />
                <div className="flex-1">
                  <p className="text-sm text-muted-foreground">Logo preview</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Actions */}
      {claim.status === "pending" && (
        <Card>
          <CardHeader>
            <CardTitle>Actions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-4">
              <Button
                onClick={handleApprove}
                disabled={approving}
                className="bg-green-600 hover:bg-green-700"
              >
                {approving ? "Approving..." : "Approve Claim"}
              </Button>
              <Button
                onClick={() => setRejectDialogOpen(true)}
                disabled={rejecting}
                variant="destructive"
              >
                Reject Claim
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Unlink Action for Approved Claims */}
      {claim.status === "approved" && (
        <Card>
          <CardHeader>
            <CardTitle>Actions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-4">
              <Button
                onClick={() => setUnlinkDialogOpen(true)}
                disabled={unlinking}
                variant="destructive"
              >
                {unlinking ? "Loskoppelen..." : "Loskoppelen"}
              </Button>
            </div>
            <p className="text-sm text-muted-foreground mt-2">
              Deze actie koppelt de locatie los van de gebruiker en verstuurt een afwijzingsmail.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Reject Dialog */}
      <Dialog open={rejectDialogOpen} onOpenChange={setRejectDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reject Claim</DialogTitle>
            <DialogDescription>
              Please provide a reason for rejecting this claim (optional).
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="rejection-reason">Rejection Reason</Label>
              <Textarea
                id="rejection-reason"
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                placeholder="Optional reason for rejection..."
                rows={4}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRejectDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleReject} disabled={rejecting}>
              {rejecting ? "Rejecting..." : "Reject Claim"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Unlink Dialog */}
      <Dialog open={unlinkDialogOpen} onOpenChange={setUnlinkDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Locatie Loskoppelen</DialogTitle>
            <DialogDescription>
              Deze actie koppelt de locatie los van de gebruiker. De gebruiker ontvangt een afwijzingsmail.
              Geef optioneel een reden op.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="unlink-reason">Reden (optioneel)</Label>
              <Textarea
                id="unlink-reason"
                value={unlinkReason}
                onChange={(e) => setUnlinkReason(e.target.value)}
                placeholder="Optionele reden voor loskoppeling..."
                rows={4}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setUnlinkDialogOpen(false)}>
              Annuleren
            </Button>
            <Button variant="destructive" onClick={handleUnlink} disabled={unlinking}>
              {unlinking ? "Loskoppelen..." : "Loskoppelen"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

