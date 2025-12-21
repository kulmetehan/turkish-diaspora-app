import { AlertTriangle, CheckCircle2, Eye, FileX, Hash, Info } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { EventStateMetrics } from "@/lib/apiAdmin";
import { cn } from "@/lib/ui/cn";

const STATE_LABELS: Record<string, string> = {
    candidate: "Candidate",
    verified: "Verified",
    published: "Published",
    rejected: "Rejected",
};

const STATE_COLORS: Record<string, string> = {
    candidate: "bg-slate-100 text-slate-800 border-slate-200",
    verified: "bg-blue-100 text-blue-800 border-blue-200",
    published: "bg-emerald-100 text-emerald-800 border-emerald-200",
    rejected: "bg-red-100 text-red-800 border-red-200",
};

type AdminEventMetricsCardProps = {
    metrics: EventStateMetrics | null;
    loading: boolean;
};

export function AdminEventMetricsCard({ metrics, loading }: AdminEventMetricsCardProps) {
    if (loading) {
        return (
            <Card className="rounded-2xl shadow-sm">
                <CardHeader>
                    <CardTitle>Event Metrics</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    <Skeleton className="h-8 w-full" />
                    <Skeleton className="h-8 w-full" />
                    <Skeleton className="h-8 w-full" />
                </CardContent>
            </Card>
        );
    }

    if (!metrics) {
        return null;
    }

    const hasPublishedNotVisible = metrics.published_not_visible > 0;

    return (
        <Card className="rounded-2xl shadow-sm">
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <Hash className="h-5 w-5" />
                    Event Metrics
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* Total and visibility summary */}
                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1">
                        <p className="text-sm text-muted-foreground">Total Events</p>
                        <p className="text-2xl font-semibold">{metrics.total_candidates}</p>
                    </div>
                    <div className="space-y-1">
                        <p className="text-sm text-muted-foreground flex items-center gap-1">
                            <Eye className="h-4 w-4" />
                            Visible on Frontend
                        </p>
                        <p className="text-2xl font-semibold text-emerald-600">
                            {metrics.visible_in_frontend}
                        </p>
                    </div>
                </div>

                {/* State distribution */}
                <div className="space-y-2">
                    <p className="text-sm font-medium text-muted-foreground">State Distribution</p>
                    <div className="flex flex-wrap gap-2">
                        {Object.entries(metrics.by_state)
                            .sort(([a], [b]) => {
                                const order = ["candidate", "verified", "published", "rejected"];
                                return order.indexOf(a) - order.indexOf(b);
                            })
                            .map(([state, count]) => (
                                <Badge
                                    key={state}
                                    variant="outline"
                                    className={cn(STATE_COLORS[state] || "bg-gray-100 text-gray-800")}
                                >
                                    {STATE_LABELS[state] || state}: {count}
                                </Badge>
                            ))}
                    </div>
                </div>

                {/* Additional metrics */}
                <div className="grid grid-cols-2 gap-4 pt-2 border-t">
                    <div className="space-y-1">
                        <p className="text-sm text-muted-foreground">Events Marked as Duplicates</p>
                        <p className="text-lg font-medium">{metrics.duplicate_count}</p>
                        <p className="text-xs text-muted-foreground">
                            Events automatically marked as duplicates (similarity ≥82% within 48h)
                        </p>
                    </div>
                    <div className="space-y-1">
                        <p className="text-sm text-muted-foreground">Canonical Events with Duplicates</p>
                        <p className="text-lg font-medium">{metrics.canonical_with_duplicates}</p>
                        <p className="text-xs text-muted-foreground">
                            Canonical events that have duplicates
                        </p>
                    </div>
                    {hasPublishedNotVisible && (
                        <div className="space-y-1">
                            <p className="text-sm text-muted-foreground flex items-center gap-1">
                                <AlertTriangle className="h-4 w-4 text-amber-600" />
                                Published Not Visible
                            </p>
                            <p className="text-lg font-medium text-amber-600">
                                {metrics.published_not_visible}
                            </p>
                            <p className="text-xs text-muted-foreground">
                                Filtered by country/location
                            </p>
                        </div>
                    )}
                </div>

                {/* Warning message if published events not visible */}
                {hasPublishedNotVisible && (
                    <div className="rounded-lg bg-amber-50 border border-amber-200 p-3">
                        <div className="flex items-start gap-2">
                            <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
                            <div className="space-y-1">
                                <p className="text-sm font-medium text-amber-900">
                                    {metrics.published_not_visible} published event
                                    {metrics.published_not_visible !== 1 ? "s" : ""} not visible
                                </p>
                                <p className="text-xs text-amber-700">
                                    These events are published but filtered out by the events_public
                                    view (likely due to country/location filters). They won't appear
                                    on the frontend until geocoding or location data is updated.
                                </p>
                            </div>
                        </div>
                    </div>
                )}

                {/* Success message if all published events are visible */}
                {!hasPublishedNotVisible && metrics.by_state.published > 0 && (
                    <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-3">
                        <div className="flex items-start gap-2">
                            <CheckCircle2 className="h-5 w-5 text-emerald-600 mt-0.5 flex-shrink-0" />
                            <div>
                                <p className="text-sm font-medium text-emerald-900">
                                    All published events are visible on the frontend
                                </p>
                            </div>
                        </div>
                    </div>
                )}

                {/* Duplicate explanation */}
                {metrics.duplicate_count > 0 && (
                    <div className="rounded-lg bg-blue-50 border border-blue-200 p-3 mt-2">
                        <div className="flex items-start gap-2">
                            <Info className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
                            <div className="space-y-1">
                                <p className="text-xs font-medium text-blue-900">About Duplicates</p>
                                <p className="text-xs text-blue-700">
                                    Events are automatically marked as duplicates if they have ≥82% similarity 
                                    (title, location, time) with another event within 48 hours. The first event 
                                    becomes "Canonical", others become "Duplicate". Check the "Duplicate Status" 
                                    column in the table to see which events are duplicates and their canonical event.
                                </p>
                            </div>
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}

