import AdminLocationsTable from "@/components/admin/AdminLocationsTable";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { lazy, Suspense } from "react";
const MetricsDashboard = lazy(() => import("@/components/admin/MetricsDashboard"));

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


