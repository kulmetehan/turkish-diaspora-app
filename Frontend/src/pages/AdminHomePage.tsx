import AdminLocationsTable from "@/components/admin/AdminLocationsTable";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

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
                                <div className="text-sm text-muted-foreground">Metrics dashboard komt hier binnenkort.</div>
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


