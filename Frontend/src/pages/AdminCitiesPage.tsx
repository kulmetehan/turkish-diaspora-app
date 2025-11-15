import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { getCitiesOverview, CityReadiness } from "@/lib/api";
import { toast } from "sonner";

function getReadinessBadgeVariant(
  status: CityReadiness["readiness_status"]
): "default" | "secondary" | "outline" {
  switch (status) {
    case "active":
      return "default";
    case "configured_inactive":
      return "secondary";
    case "config_incomplete":
      return "outline";
    default:
      return "outline";
  }
}

function formatReadinessStatus(status: CityReadiness["readiness_status"]): string {
  switch (status) {
    case "active":
      return "Active";
    case "configured_inactive":
      return "Configured but Inactive";
    case "config_incomplete":
      return "Config Incomplete";
    default:
      return status;
  }
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function formatGrowth(value: number | null): string {
  if (value === null) return "N/A";
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

export default function AdminCitiesPage() {
  const [cities, setCities] = useState<CityReadiness[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadCities() {
      try {
        setLoading(true);
        setError(null);
        const data = await getCitiesOverview();
        setCities(data.cities);
      } catch (err: any) {
        const message = err?.message || "Failed to load cities overview";
        setError(message);
        toast.error(message);
      } finally {
        setLoading(false);
      }
    }

    loadCities();
  }, []);

  if (loading) {
    return (
      <div className="p-6">
        <div className="text-sm text-muted-foreground">Loading cities overview…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="text-sm text-destructive">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Cities Overview</h1>
      </header>

      <div className="text-sm text-muted-foreground mb-4">
        Overview of city configuration and metrics to support multi-city rollout.
      </div>

      {cities.length === 0 ? (
        <Card className="rounded-2xl shadow-sm">
          <CardContent className="p-6">
            <div className="text-sm text-muted-foreground">No cities configured yet.</div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {cities.map((city) => (
            <Card key={city.city_key} className="rounded-2xl shadow-sm">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>{city.city_name}</CardTitle>
                  <Badge variant={getReadinessBadgeVariant(city.readiness_status)}>
                    {formatReadinessStatus(city.readiness_status)}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <div className="text-muted-foreground">Districts</div>
                      <div className="font-medium">
                        {city.has_districts ? city.districts_count : "None"}
                      </div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">Coverage</div>
                      <div className="font-medium">{formatPercent(city.coverage_ratio)}</div>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <div className="text-muted-foreground">Verified</div>
                      <div className="font-medium">{city.verified_count}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">Candidates</div>
                      <div className="font-medium">{city.candidate_count}</div>
                    </div>
                  </div>
                  {city.growth_weekly !== null && (
                    <div className="text-sm">
                      <div className="text-muted-foreground">Weekly Growth</div>
                      <div className="font-medium">{formatGrowth(city.growth_weekly)}</div>
                    </div>
                  )}
                </div>

                {city.readiness_notes && (
                  <div className="pt-2 border-t">
                    <div className="text-xs text-muted-foreground">{city.readiness_notes}</div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

