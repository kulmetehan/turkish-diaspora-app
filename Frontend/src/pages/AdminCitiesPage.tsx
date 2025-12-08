import CityFormDialog, { type CityFormValues } from "@/components/admin/CityFormDialog";
import DistrictFormDialog, { type DistrictFormValues } from "@/components/admin/DistrictFormDialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CityReadiness } from "@/lib/api";
import {
  createCity,
  createDistrict,
  deleteCity,
  deleteDistrict,
  getCitiesOverview as getAdminCitiesOverview,
  getCityDetail,
  updateCity,
  updateDistrict,
  type CityCreate,
  type CityDetailResponse,
  type CityUpdate,
  type DistrictCreate,
  type DistrictUpdate
} from "@/lib/apiAdmin";
import { useEffect, useState } from "react";
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

  // Dialog states
  const [cityDialogOpen, setCityDialogOpen] = useState(false);
  const [districtDialogOpen, setDistrictDialogOpen] = useState(false);
  const [editingCity, setEditingCity] = useState<CityReadiness | null>(null);
  const [editingDistrict, setEditingDistrict] = useState<{ key: string; cityKey: string; name: string; center_lat?: number; center_lng?: number } | null>(null);
  const [districtCityKey, setDistrictCityKey] = useState<string>("");
  const [saving, setSaving] = useState(false);

  // Expanded cities and city details cache
  const [expandedCities, setExpandedCities] = useState<Set<string>>(new Set());
  const [cityDetailsCache, setCityDetailsCache] = useState<Map<string, CityDetailResponse>>(new Map());
  const [loadingDistricts, setLoadingDistricts] = useState<Set<string>>(new Set());

  async function loadCities() {
    try {
      setLoading(true);
      setError(null);
      const data = await getAdminCitiesOverview();
      setCities(data.cities);
    } catch (err: any) {
      const message = err?.message || "Failed to load cities overview";
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadCities();
  }, []);

  const toggleCityExpanded = async (cityKey: string) => {
    const isCurrentlyExpanded = expandedCities.has(cityKey);

    if (isCurrentlyExpanded) {
      // Collapse
      setExpandedCities((prev) => {
        const newSet = new Set(prev);
        newSet.delete(cityKey);
        return newSet;
      });
    } else {
      // Expand - load city details if not cached
      setExpandedCities((prev) => new Set(prev).add(cityKey));

      if (!cityDetailsCache.has(cityKey)) {
        setLoadingDistricts((prev) => new Set(prev).add(cityKey));
        try {
          const cityDetail = await getCityDetail(cityKey);
          setCityDetailsCache((prev) => {
            const newMap = new Map(prev);
            newMap.set(cityKey, cityDetail);
            return newMap;
          });
        } catch (err: any) {
          toast.error(err?.message || `Failed to load districts for ${cityKey}`);
          // Collapse on error
          setExpandedCities((prev) => {
            const newSet = new Set(prev);
            newSet.delete(cityKey);
            return newSet;
          });
        } finally {
          setLoadingDistricts((prev) => {
            const newSet = new Set(prev);
            newSet.delete(cityKey);
            return newSet;
          });
        }
      }
    }
  };

  const invalidateCityCache = (cityKey: string) => {
    setCityDetailsCache((prev) => {
      const newMap = new Map(prev);
      newMap.delete(cityKey);
      return newMap;
    });
  };

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

  const handleCreateCity = async (values: CityFormValues) => {
    setSaving(true);
    try {
      const payload: CityCreate = {
        city_name: values.city_name,
        country: values.country,
        center_lat: values.center_lat,
        center_lng: values.center_lng,
      };
      await createCity(payload);
      toast.success("City created successfully");
      setCityDialogOpen(false);
      await loadCities();
    } catch (err: any) {
      toast.error(err?.message || "Failed to create city");
      throw err;
    } finally {
      setSaving(false);
    }
  };

  const handleUpdateCity = async (values: CityFormValues) => {
    if (!editingCity) return;
    setSaving(true);
    try {
      const payload: CityUpdate = {
        city_name: values.city_name,
        country: values.country,
        center_lat: values.center_lat,
        center_lng: values.center_lng,
      };
      await updateCity(editingCity.city_key, payload);
      toast.success("City updated successfully");
      setCityDialogOpen(false);
      invalidateCityCache(editingCity.city_key);
      setEditingCity(null);
      await loadCities();
    } catch (err: any) {
      toast.error(err?.message || "Failed to update city");
      throw err;
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteCity = async (city: CityReadiness) => {
    if (!window.confirm(`Are you sure you want to delete "${city.city_name}"? This will also delete all districts.`)) {
      return;
    }
    setSaving(true);
    try {
      await deleteCity(city.city_key);
      toast.success("City deleted successfully");
      invalidateCityCache(city.city_key);
      setExpandedCities((prev) => {
        const newSet = new Set(prev);
        newSet.delete(city.city_key);
        return newSet;
      });
      await loadCities();
    } catch (err: any) {
      toast.error(err?.message || "Failed to delete city");
    } finally {
      setSaving(false);
    }
  };

  const handleCreateDistrict = async (values: DistrictFormValues) => {
    setSaving(true);
    try {
      const payload: DistrictCreate = {
        name: values.name,
        center_lat: values.center_lat,
        center_lng: values.center_lng,
      };
      await createDistrict(districtCityKey, payload);
      toast.success("District created successfully");
      setDistrictDialogOpen(false);
      invalidateCityCache(districtCityKey);
      setDistrictCityKey("");
      await loadCities();
    } catch (err: any) {
      toast.error(err?.message || "Failed to create district");
      throw err;
    } finally {
      setSaving(false);
    }
  };

  const handleUpdateDistrict = async (values: DistrictFormValues) => {
    if (!editingDistrict) return;
    setSaving(true);
    try {
      const payload: DistrictUpdate = {
        name: values.name,
        center_lat: values.center_lat,
        center_lng: values.center_lng,
      };
      const response = await updateDistrict(editingDistrict.cityKey, editingDistrict.key, payload);
      toast.success("District updated successfully");
      setDistrictDialogOpen(false);
      
      // Always invalidate cache - key might have changed
      invalidateCityCache(editingDistrict.cityKey);
      
      // If key changed, need to refresh everything
      if (response.district_key !== editingDistrict.key) {
        // Key changed - reset editing district state
        setEditingDistrict(null);
        // Reload cities to get updated counts
        await loadCities();
      } else {
        // Key didn't change, just reset editing state
        setEditingDistrict(null);
      }
    } catch (err: any) {
      toast.error(err?.message || "Failed to update district");
      throw err;
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteDistrict = async (cityKey: string, districtKey: string, districtName: string) => {
    if (!window.confirm(`Are you sure you want to delete district "${districtName}"?`)) {
      return;
    }
    setSaving(true);
    try {
      await deleteDistrict(cityKey, districtKey);
      toast.success("District deleted successfully");
      invalidateCityCache(cityKey);
      await loadCities();
    } catch (err: any) {
      toast.error(err?.message || "Failed to delete district");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 space-y-4">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Cities Overview</h1>
        <Button onClick={() => { setEditingCity(null); setCityDialogOpen(true); }}>
          Add City
        </Button>
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

                {/* Districts section */}
                {city.has_districts && (
                  <div className="pt-2 border-t">
                    <Button
                      size="sm"
                      variant="ghost"
                      className="w-full justify-between"
                      onClick={() => toggleCityExpanded(city.city_key)}
                      disabled={saving || loadingDistricts.has(city.city_key)}
                    >
                      <span className="text-sm font-medium">
                        Districts ({city.districts_count})
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {expandedCities.has(city.city_key) ? "▼ Collapse" : "▶ Expand"}
                      </span>
                    </Button>

                    {expandedCities.has(city.city_key) && (
                      <div className="mt-2 space-y-2">
                        {loadingDistricts.has(city.city_key) ? (
                          <div className="text-xs text-muted-foreground">Loading districts...</div>
                        ) : (
                          (() => {
                            const cityDetail = cityDetailsCache.get(city.city_key);
                            if (!cityDetail || cityDetail.districts.length === 0) {
                              return <div className="text-xs text-muted-foreground">No districts found</div>;
                            }
                            return cityDetail.districts.map((district) => (
                              <div
                                key={district.key}
                                className="flex items-center justify-between p-2 bg-gray-50 rounded text-sm"
                              >
                                <div className="flex-1 min-w-0">
                                  <div className="font-medium truncate">{district.name}</div>
                                  <div className="text-xs text-muted-foreground">
                                    {district.center_lat.toFixed(6)}, {district.center_lng.toFixed(6)}
                                  </div>
                                </div>
                                <div className="flex gap-1 ml-2">
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    className="h-7 px-2"
                                    onClick={() => {
                                      setEditingDistrict({
                                        key: district.key,
                                        cityKey: city.city_key,
                                        name: district.name,
                                        center_lat: district.center_lat,
                                        center_lng: district.center_lng,
                                      });
                                      setDistrictCityKey(city.city_key);
                                      setDistrictDialogOpen(true);
                                    }}
                                    disabled={saving}
                                  >
                                    Edit
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    className="h-7 px-2 text-red-600 hover:text-red-700"
                                    onClick={() => handleDeleteDistrict(city.city_key, district.key, district.name)}
                                    disabled={saving}
                                  >
                                    Delete
                                  </Button>
                                </div>
                              </div>
                            ));
                          })()
                        )}
                      </div>
                    )}
                  </div>
                )}

                <div className="pt-2 border-t flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setEditingCity(city);
                      setCityDialogOpen(true);
                    }}
                    disabled={saving}
                  >
                    Edit
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setDistrictCityKey(city.city_key);
                      setEditingDistrict(null);
                      setDistrictDialogOpen(true);
                    }}
                    disabled={saving}
                  >
                    Add District
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() => handleDeleteCity(city)}
                    disabled={saving}
                  >
                    Delete
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <CityFormDialog
        open={cityDialogOpen}
        onOpenChange={(open) => {
          setCityDialogOpen(open);
          if (!open) setEditingCity(null);
        }}
        initialCity={editingCity}
        onSubmit={editingCity ? handleUpdateCity : handleCreateCity}
        loading={saving}
      />

      <DistrictFormDialog
        open={districtDialogOpen}
        onOpenChange={(open) => {
          setDistrictDialogOpen(open);
          if (!open) {
            setEditingDistrict(null);
            setDistrictCityKey("");
          }
        }}
        cityKey={districtCityKey}
        initialDistrict={editingDistrict}
        onSubmit={editingDistrict ? handleUpdateDistrict : handleCreateDistrict}
        loading={saving}
      />
    </div>
  );
}

