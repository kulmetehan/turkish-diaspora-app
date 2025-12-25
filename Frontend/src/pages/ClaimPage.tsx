// Frontend/src/pages/ClaimPage.tsx
import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import {
  getTokenClaimInfo,
  claimLocationByToken,
  removeLocationByToken,
  submitCorrectionByToken,
  type TokenClaimResponse,
} from "@/lib/api";
import { ArrowLeft, Mail, AlertCircle, CheckCircle2, Edit } from "lucide-react";

export default function ClaimPage() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const [claimInfo, setClaimInfo] = useState<TokenClaimResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Claim form state
  const [claimEmail, setClaimEmail] = useState("");
  const [claimDescription, setClaimDescription] = useState("");
  const [isClaiming, setIsClaiming] = useState(false);

  // Remove dialog state
  const [showRemoveDialog, setShowRemoveDialog] = useState(false);
  const [removeReason, setRemoveReason] = useState("");
  const [isRemoving, setIsRemoving] = useState(false);

  // Correction form state
  const [showCorrectionDialog, setShowCorrectionDialog] = useState(false);
  const [correctionDetails, setCorrectionDetails] = useState("");
  const [isSubmittingCorrection, setIsSubmittingCorrection] = useState(false);

  useEffect(() => {
    const loadClaimInfo = async () => {
      if (!token) {
        setError("Geen token opgegeven");
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const data = await getTokenClaimInfo(token);
        setClaimInfo(data);
      } catch (err: any) {
        console.error("Failed to load claim info:", err);
        const errorMessage = err.message || err.detail || "Fout bij laden van claim informatie";
        setError(errorMessage);
        toast.error(errorMessage);
      } finally {
        setLoading(false);
      }
    };

    loadClaimInfo();
  }, [token]);

  const handleBack = () => {
    navigate("/map");
  };

  const handleClaim = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!claimEmail.trim()) {
      toast.error("Email is verplicht");
      return;
    }

    if (!token) return;

    setIsClaiming(true);
    try {
      await claimLocationByToken(token, claimEmail.trim(), claimDescription.trim() || undefined);
      toast.success("Claim succesvol ingediend!");
      
      // Reload claim info to show updated status
      const updatedInfo = await getTokenClaimInfo(token);
      setClaimInfo(updatedInfo);
      
      // Reset form
      setClaimEmail("");
      setClaimDescription("");
    } catch (err: any) {
      const errorMessage = err.message || err.detail || "Fout bij indienen van claim";
      toast.error(errorMessage);
    } finally {
      setIsClaiming(false);
    }
  };

  const handleRemove = async () => {
    if (!token) return;

    setIsRemoving(true);
    try {
      await removeLocationByToken(token, removeReason.trim() || undefined);
      toast.success("Locatie is verwijderd. Bedankt voor uw feedback.");
      
      // Reload claim info
      const updatedInfo = await getTokenClaimInfo(token);
      setClaimInfo(updatedInfo);
      
      // Reset and close dialog
      setRemoveReason("");
      setShowRemoveDialog(false);
    } catch (err: any) {
      const errorMessage = err.message || err.detail || "Fout bij verwijderen van locatie";
      toast.error(errorMessage);
    } finally {
      setIsRemoving(false);
    }
  };

  const handleSubmitCorrection = async () => {
    if (!correctionDetails.trim() || correctionDetails.trim().length < 3) {
      toast.error("Correctie details moeten minimaal 3 karakters bevatten");
      return;
    }

    if (!token) return;

    setIsSubmittingCorrection(true);
    try {
      await submitCorrectionByToken(token, correctionDetails.trim());
      toast.success("Correctie succesvol ingediend. We verwerken dit zo snel mogelijk.");
      
      // Reset and close dialog
      setCorrectionDetails("");
      setShowCorrectionDialog(false);
    } catch (err: any) {
      const errorMessage = err.message || err.detail || "Fout bij indienen van correctie";
      toast.error(errorMessage);
    } finally {
      setIsSubmittingCorrection(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen p-4">
        <Card className="max-w-md w-full">
          <CardContent className="p-6">
            <div className="text-center text-sm text-foreground/70">Laden...</div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error || !claimInfo) {
    return (
      <div className="flex items-center justify-center min-h-screen p-4">
        <Card className="max-w-md w-full">
          <CardContent className="p-6">
            <div className="text-center text-sm text-destructive mb-4">
              {error || "Claim informatie niet gevonden"}
            </div>
            <div className="text-center text-xs text-muted-foreground mb-4">
              Het token is mogelijk ongeldig of verlopen.
            </div>
            <div className="text-center">
              <Button onClick={handleBack} variant="outline" size="sm">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Terug naar kaart
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-screen p-4">
      <Card className="max-w-md w-full">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Button onClick={handleBack} variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Terug
            </Button>
          </div>
          <CardTitle className="text-xl">Locatie Claim</CardTitle>
          {claimInfo.location_name && (
            <p className="text-sm text-muted-foreground mt-1">{claimInfo.location_name}</p>
          )}
          {claimInfo.location_address && (
            <p className="text-xs text-muted-foreground">{claimInfo.location_address}</p>
          )}
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Status Display */}
          <div className="flex items-center gap-2 p-3 rounded-lg bg-muted">
            {claimInfo.claim_status === "unclaimed" && (
              <>
                <AlertCircle className="w-5 h-5 text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium">Nog niet geclaimed</p>
                  <p className="text-xs text-muted-foreground">Claim deze locatie om eigenaar te worden</p>
                </div>
              </>
            )}
            {claimInfo.claim_status === "claimed_free" && (
              <>
                <CheckCircle2 className="w-5 h-5 text-green-600" />
                <div>
                  <p className="text-sm font-medium">Geclaimed</p>
                  <p className="text-xs text-muted-foreground">
                    Gratis periode actief tot{" "}
                    {claimInfo.free_until
                      ? new Date(claimInfo.free_until).toLocaleDateString("nl-NL")
                      : "onbekend"}
                  </p>
                </div>
              </>
            )}
            {claimInfo.claim_status === "expired" && (
              <>
                <AlertCircle className="w-5 h-5 text-orange-600" />
                <div>
                  <p className="text-sm font-medium">Gratis periode verlopen</p>
                  <p className="text-xs text-muted-foreground">De gratis periode is afgelopen</p>
                </div>
              </>
            )}
            {claimInfo.claim_status === "removed" && (
              <>
                <AlertCircle className="w-5 h-5 text-red-600" />
                <div>
                  <p className="text-sm font-medium">Verwijderd</p>
                  <p className="text-xs text-muted-foreground">
                    Deze locatie is verwijderd door de eigenaar
                  </p>
                </div>
              </>
            )}
          </div>

          {/* Claim Form - Only show if unclaimed */}
          {claimInfo.claim_status === "unclaimed" && (
            <form onSubmit={handleClaim} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="claim-email">
                  Email adres <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="claim-email"
                  type="email"
                  placeholder="uw@email.nl"
                  value={claimEmail}
                  onChange={(e) => setClaimEmail(e.target.value)}
                  disabled={isClaiming}
                  required
                />
                <p className="text-xs text-muted-foreground">
                  We gebruiken dit om contact met u op te nemen over uw claim
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="claim-description">Beschrijving (optioneel)</Label>
                <Textarea
                  id="claim-description"
                  placeholder="Optionele opmerkingen of aanvullende informatie..."
                  value={claimDescription}
                  onChange={(e) => setClaimDescription(e.target.value)}
                  disabled={isClaiming}
                  rows={4}
                  maxLength={2000}
                />
                <p className="text-xs text-muted-foreground">
                  {claimDescription.length} / 2000 karakters
                </p>
              </div>

              <Button type="submit" disabled={isClaiming || !claimEmail.trim()} className="w-full">
                {isClaiming ? "Indienen..." : "Claim Locatie"}
              </Button>
            </form>
          )}

          {/* Action Buttons - Show if claimed */}
          {claimInfo.claim_status === "claimed_free" && (
            <div className="space-y-3">
              <Button
                variant="destructive"
                onClick={() => setShowRemoveDialog(true)}
                className="w-full"
              >
                Locatie Verwijderen
              </Button>
              <Button
                variant="outline"
                onClick={() => setShowCorrectionDialog(true)}
                className="w-full"
              >
                <Edit className="w-4 h-4 mr-2" />
                Correctie Indienen
              </Button>
            </div>
          )}

          {/* Action Buttons - Show if expired */}
          {claimInfo.claim_status === "expired" && (
            <div className="space-y-3">
              <Button
                variant="destructive"
                onClick={() => setShowRemoveDialog(true)}
                className="w-full"
              >
                Locatie Verwijderen
              </Button>
              <Button
                variant="outline"
                onClick={() => setShowCorrectionDialog(true)}
                className="w-full"
              >
                <Edit className="w-4 h-4 mr-2" />
                Correctie Indienen
              </Button>
            </div>
          )}

          {/* Info - Show if removed */}
          {claimInfo.claim_status === "removed" && (
            <div className="p-4 bg-muted rounded-lg">
              <p className="text-sm text-muted-foreground">
                Deze locatie is verwijderd. Als u vragen heeft, neem dan contact met ons op.
              </p>
              {claimInfo.removal_reason && (
                <p className="text-xs text-muted-foreground mt-2">
                  Reden: {claimInfo.removal_reason}
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Remove Confirmation Dialog */}
      <Dialog open={showRemoveDialog} onOpenChange={setShowRemoveDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Locatie Verwijderen</DialogTitle>
            <DialogDescription>
              Weet u zeker dat u deze locatie wilt verwijderen? Deze actie kan niet ongedaan worden
              gemaakt.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="remove-reason">Reden (optioneel)</Label>
              <Textarea
                id="remove-reason"
                placeholder="Waarom wilt u deze locatie verwijderen? (optioneel)"
                value={removeReason}
                onChange={(e) => setRemoveReason(e.target.value)}
                disabled={isRemoving}
                rows={3}
                maxLength={500}
              />
              <p className="text-xs text-muted-foreground">{removeReason.length} / 500 karakters</p>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowRemoveDialog(false);
                setRemoveReason("");
              }}
              disabled={isRemoving}
            >
              Annuleren
            </Button>
            <Button variant="destructive" onClick={handleRemove} disabled={isRemoving}>
              {isRemoving ? "Verwijderen..." : "Ja, Verwijderen"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Correction Dialog */}
      <Dialog open={showCorrectionDialog} onOpenChange={setShowCorrectionDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Correctie Indienen</DialogTitle>
            <DialogDescription>
              Heeft u een correctie of opmerking over deze locatie? Laat het ons weten.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="correction-details">
                Correctie details <span className="text-destructive">*</span>
              </Label>
              <Textarea
                id="correction-details"
                placeholder="Beschrijf uw correctie of opmerking..."
                value={correctionDetails}
                onChange={(e) => setCorrectionDetails(e.target.value)}
                disabled={isSubmittingCorrection}
                rows={6}
                maxLength={2000}
                required
              />
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>
                  {correctionDetails.length < 3
                    ? `Minimaal ${3 - correctionDetails.length} karakters nodig`
                    : "✓"}
                </span>
                <span>{correctionDetails.length} / 2000 karakters</span>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowCorrectionDialog(false);
                setCorrectionDetails("");
              }}
              disabled={isSubmittingCorrection}
            >
              Annuleren
            </Button>
            <Button
              onClick={handleSubmitCorrection}
              disabled={isSubmittingCorrection || correctionDetails.trim().length < 3}
            >
              {isSubmittingCorrection ? "Indienen..." : "Correctie Indienen"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
