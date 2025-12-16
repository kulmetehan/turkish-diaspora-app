import { Suspense, useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import DiscoveryCoverageSummary from "@/components/admin/DiscoveryCoverageSummary";
import AdminDiscoveryMap from "@/components/admin/AdminDiscoveryMap";
import { getCitiesOverview, type CityReadiness } from "@/lib/api";

export default function DiscoveryPage() {
  const [selectedCity, setSelectedCity] = useState<string>("rotterdam");
  const [cities, setCities] = useState<CityReadiness[]>([]);
  const [citiesLoading, setCitiesLoading] = useState<boolean>(true);
  const [citiesError, setCitiesError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setCitiesLoading(true);
        setCitiesError(null);
        const overview = await getCitiesOverview();
        if (!cancelled) {
          setCities(overview.cities);
          if (overview.cities.length > 0) {
            const firstCityWithDistricts = overview.cities.find(c => c.has_districts);
            if (firstCityWithDistricts && selectedCity === "rotterdam") {
              setSelectedCity(firstCityWithDistricts.city_key);
            }
          }
        }
      } catch (e: any) {
        if (!cancelled) {
          console.warn("Failed to load cities overview:", e);
          setCitiesError(e?.message || "Failed to load cities");
        }
      } finally {
        if (!cancelled) {
          setCitiesLoading(false);
        }
      }
    })();
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Discovery Coverage</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Visualize discovery grid coverage and statistics per city
        </p>
      </div>
      <Suspense fallback={<div className="text-sm text-muted-foreground p-4">Loading coverage visualization…</div>}>
        <div className="space-y-4">
          <DiscoveryCoverageSummary city={selectedCity} cities={cities} />
          <Card className="rounded-2xl shadow-sm">
            <CardHeader>
              <CardTitle>Discovery Grid Coverage Map</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="relative w-full h-[600px] min-h-[400px]">
                <AdminDiscoveryMap 
                  selectedCity={selectedCity}
                  onCityChange={setSelectedCity}
                  cities={cities}
                  citiesLoading={citiesLoading}
                  citiesError={citiesError}
                />
              </div>
            </CardContent>
          </Card>
        </div>
      </Suspense>
    </div>
  );
}





















