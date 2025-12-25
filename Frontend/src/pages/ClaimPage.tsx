// Frontend/src/pages/ClaimPage.tsx
import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { apiFetch } from "@/lib/api";
import { ArrowLeft } from "lucide-react";

interface TokenClaimResponse {
  location_id: number;
  location_name: string | null;
  location_address: string | null;
  location_category: string | null;
  claim_token: string;
  claim_status: string;
  claimed_by_email: string | null;
  claimed_at: string | null;
  free_until: string | null;
  removed_at: string | null;
  removal_reason: string | null;
}

export default function ClaimPage() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const [claimInfo, setClaimInfo] = useState<TokenClaimResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
        const data = await apiFetch<TokenClaimResponse>(`/api/v1/claims/${token}`);
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

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Card className="p-6 max-w-md w-full">
          <div className="text-center text-sm text-foreground/70">Laden...</div>
        </Card>
      </div>
    );
  }

  if (error || !claimInfo) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Card className="p-6 max-w-md w-full">
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
        </Card>
      </div>
    );
  }

  // Placeholder UI - full implementation will come in outreach plan (Fase 7)
  return (
    <div className="flex items-center justify-center min-h-screen p-4">
      <Card className="p-6 max-w-md w-full">
        <div className="mb-4">
          <Button onClick={handleBack} variant="ghost" size="sm" className="mb-4">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Terug
          </Button>
          <h1 className="text-xl font-semibold mb-2">Locatie Claim</h1>
          {claimInfo.location_name && (
            <p className="text-sm text-muted-foreground mb-4">{claimInfo.location_name}</p>
          )}
        </div>

        <div className="space-y-4">
          <div>
            <p className="text-sm font-medium mb-1">Status</p>
            <p className="text-sm text-muted-foreground capitalize">{claimInfo.claim_status}</p>
          </div>

          {claimInfo.claim_status === "unclaimed" && (
            <div className="p-4 bg-muted rounded-lg">
              <p className="text-sm text-muted-foreground">
                Deze locatie kan worden geclaimed. De volledige claim functionaliteit wordt binnenkort toegevoegd.
              </p>
            </div>
          )}

          {claimInfo.claim_status === "claimed_free" && (
            <div className="p-4 bg-muted rounded-lg">
              <p className="text-sm text-muted-foreground">
                Deze locatie is al geclaimed. Gratis periode actief tot{" "}
                {claimInfo.free_until
                  ? new Date(claimInfo.free_until).toLocaleDateString("nl-NL")
                  : "onbekend"}
                .
              </p>
            </div>
          )}

          {claimInfo.claim_status === "expired" && (
            <div className="p-4 bg-muted rounded-lg">
              <p className="text-sm text-muted-foreground">
                De gratis periode voor deze locatie is verlopen.
              </p>
            </div>
          )}

          {claimInfo.claim_status === "removed" && (
            <div className="p-4 bg-muted rounded-lg">
              <p className="text-sm text-muted-foreground">
                Deze locatie is verwijderd door de eigenaar.
              </p>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}

