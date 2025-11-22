import AdminLocationsTable from "@/components/admin/AdminLocationsTable";
import NewsAIDiagnosticsPanel from "@/components/admin/NewsAIDiagnosticsPanel";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { lazy, Suspense, useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { getCitiesOverview, type CityReadiness } from "@/lib/api";
const MetricsDashboard = lazy(() => import("@/components/admin/MetricsDashboard"));
const AdminDiscoveryMap = lazy(() => import("@/components/admin/AdminDiscoveryMap"));
const DiscoveryCoverageSummary = lazy(() => import("@/components/admin/DiscoveryCoverageSummary"));
const AdminAIPolicyPage = lazy(() => import("@/pages/AdminAIPolicyPage"));
const TasksPanel = lazy(() => import("@/components/admin/TasksPanel"));

export default function AdminHomePage() {
    // City state for Discovery Coverage tab
    const [selectedCity, setSelectedCity] = useState<string>("rotterdam");
    const [cities, setCities] = useState<CityReadiness[]>([]);
    const [citiesLoading, setCitiesLoading] = useState<boolean>(true);
    const [citiesError, setCitiesError] = useState<string | null>(null);

    // Load cities on mount
    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                setCitiesLoading(true);
                setCitiesError(null);
                const overview = await getCitiesOverview();
                if (!cancelled) {
                    setCities(overview.cities);
                    // Auto-select first city with districts if available, otherwise keep "rotterdam"
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
            <header className="flex items-center justify-between">
                <h1 className="text-2xl font-semibold">Admin Dashboard</h1>
                <div className="flex gap-2">
                    <Link to="/admin/cities">
                        <Button variant="outline">Cities</Button>
                    </Link>
                    <Link to="/admin/workers">
                        <Button variant="outline">Workers</Button>
                    </Link>
                </div>
            </header>

            <Card className="rounded-2xl shadow-sm">
                <CardHeader>
                    <CardTitle>Beheer</CardTitle>
                </CardHeader>
                <CardContent>
                    <Tabs defaultValue="locations">
                        <TabsList>
                            <TabsTrigger value="locations">Locations</TabsTrigger>
                            <TabsTrigger value="metrics">Metrics</TabsTrigger>
                            <TabsTrigger value="workers">Workers</TabsTrigger>
                            <TabsTrigger value="tasks">Tasks</TabsTrigger>
                            <TabsTrigger value="news-ai">News AI Logs</TabsTrigger>
                            <TabsTrigger value="coverage">Discovery Coverage</TabsTrigger>
                            <TabsTrigger value="ai-policy">AI Policy</TabsTrigger>
                            <TabsTrigger value="audit">Audit Log (coming soon)</TabsTrigger>
                        </TabsList>
                        <div className="mt-4">
                            <TabsContent value="locations">
                                <AdminLocationsTable />
                            </TabsContent>
                            <TabsContent value="metrics">
                                <Suspense fallback={<div className="text-sm text-muted-foreground p-4">Loading metrics…</div>}>
                                    <MetricsDashboard />
                                </Suspense>
                            </TabsContent>
                            <TabsContent value="workers">
                                <div className="space-y-4">
                                    <div className="text-sm text-muted-foreground">
                                        View and manage worker bots, trigger manual runs, and monitor worker status.
                                    </div>
                                    <Link to="/admin/workers">
                                        <Button>Open Workers Dashboard</Button>
                                    </Link>
                                </div>
                            </TabsContent>
                            <TabsContent value="tasks">
                                <Suspense fallback={<div className="text-sm text-muted-foreground p-4">Loading tasks…</div>}>
                                    <TasksPanel />
                                </Suspense>
                            </TabsContent>
                            <TabsContent value="news-ai">
                                <NewsAIDiagnosticsPanel />
                            </TabsContent>
                            <TabsContent value="coverage">
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
                            </TabsContent>
                            <TabsContent value="ai-policy">
                                <Suspense fallback={<div className="text-sm text-muted-foreground p-4">Loading AI policy configuration…</div>}>
                                    <AdminAIPolicyPage />
                                </Suspense>
                            </TabsContent>
                            <TabsContent value="audit">
                                <div className="text-sm text-muted-foreground">Audit log UI wordt later toegevoegd.</div>
                            </TabsContent>
                        </div>
                    </Tabs>
                </CardContent>
            </Card>
        </div>
    );
}


