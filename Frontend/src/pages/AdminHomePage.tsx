import AdminLocationsTable from "@/components/admin/AdminLocationsTable";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { lazy, Suspense } from "react";
import { Link } from "react-router-dom";
const MetricsDashboard = lazy(() => import("@/components/admin/MetricsDashboard"));
const AdminDiscoveryMap = lazy(() => import("@/components/admin/AdminDiscoveryMap"));
const DiscoveryCoverageSummary = lazy(() => import("@/components/admin/DiscoveryCoverageSummary"));
const AdminAIPolicyPage = lazy(() => import("@/pages/AdminAIPolicyPage"));
const TasksPanel = lazy(() => import("@/components/admin/TasksPanel"));

export default function AdminHomePage() {
    return (
        <div className="p-6 space-y-4">
            <header className="flex items-center justify-between">
                <h1 className="text-2xl font-semibold">Admin Dashboard</h1>
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
                            <TabsContent value="coverage">
                                <Suspense fallback={<div className="text-sm text-muted-foreground p-4">Loading coverage visualization…</div>}>
                                    <div className="space-y-4">
                                        <DiscoveryCoverageSummary />
                                        <Card className="rounded-2xl shadow-sm">
                                            <CardHeader>
                                                <CardTitle>Discovery Grid Coverage Map</CardTitle>
                                            </CardHeader>
                                            <CardContent>
                                                <AdminDiscoveryMap />
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


