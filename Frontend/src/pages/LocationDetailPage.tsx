import { useEffect, useState } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import UnifiedLocationDetail from "@/components/UnifiedLocationDetail";
import { ViewportProvider } from "@/contexts/viewport";
import type { LocationMarker } from "@/api/fetchLocations";
import { getLocationById } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { toast } from "sonner";
import { trackLocationView, getSourceFromLocation } from "@/lib/analytics";

export default function LocationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const [locationData, setLocationData] = useState<LocationMarker | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Normalize URL if accessed without hash (HashRouter requires #)
  // This effect runs on mount to handle direct navigation to /locations/:id
  useEffect(() => {
    const hash = window.location.hash;
    const pathname = window.location.pathname;
    
    // If pathname has /locations/ but hash doesn't start with #/, redirect
    if (pathname.startsWith("/locations/") && (!hash || !hash.startsWith("#/"))) {
      const search = window.location.search;
      const newHash = `#${pathname}${search}`;
      // Use window.location directly for immediate redirect before React Router processes
      window.location.hash = newHash;
      return;
    }
  }, []);

  useEffect(() => {
    const loadLocation = async () => {
      if (!id) {
        setError("Geen locatie ID opgegeven");
        setLoading(false);
        return;
      }

      const locationId = parseInt(id, 10);
      if (isNaN(locationId)) {
        setError("Ongeldig locatie ID");
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const data = await getLocationById(locationId);
        setLocationData(data);
        
        // Track location view after data is loaded
        const source = getSourceFromLocation(location);
        trackLocationView(locationId, source);
      } catch (err: any) {
        console.error("Failed to load location:", err);
        const errorMessage = err.message || "Fout bij laden van locatie";
        setError(errorMessage);
        toast.error(errorMessage);
      } finally {
        setLoading(false);
      }
    };

    loadLocation();
  }, [id, location]);

  const handleBack = () => {
    // Navigeer naar list view met standaard filters
    navigate("/map?feed=nl&categories=general&view=list");
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Card className="p-4">
          <div className="text-center text-sm text-foreground/70">Laden...</div>
        </Card>
      </div>
    );
  }

  if (error || !locationData) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Card className="p-4">
          <div className="text-center text-sm text-destructive">
            {error || "Locatie niet gevonden"}
          </div>
          <div className="mt-4 text-center">
            <button
              onClick={handleBack}
              className="text-sm text-primary hover:underline"
            >
              Terug
            </button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <ViewportProvider>
      <UnifiedLocationDetail
        location={locationData}
        viewMode="list"
        onBack={handleBack}
      />
    </ViewportProvider>
  );
}

