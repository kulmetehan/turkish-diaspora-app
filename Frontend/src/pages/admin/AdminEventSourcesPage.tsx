import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import EventSourceFormDialog, { type EventSourceFormValues } from "@/components/admin/EventSourceFormDialog";
import EventSourceList from "@/components/admin/EventSourceList";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { useAdminEventSources } from "@/hooks/useAdminEventSources";
import {
    createEventSourceAdmin,
    getEventMetricsAdmin,
    toggleEventSourceStatusAdmin,
    updateEventSourceAdmin,
    type EventMetricsSnapshotDTO,
    type EventSourceDTO,
} from "@/lib/apiAdmin";

export default function AdminEventSourcesPage() {
    const [statusFilter, setStatusFilter] = useState<"all" | "active" | "disabled">("all");
    const [dialogOpen, setDialogOpen] = useState(false);
    const [editingSource, setEditingSource] = useState<EventSourceDTO | null>(null);
    const [saving, setSaving] = useState(false);
    const [metrics, setMetrics] = useState<EventMetricsSnapshotDTO | null>(null);
    const [metricsLoading, setMetricsLoading] = useState(false);

    const statusParam = useMemo(() => (statusFilter === "all" ? undefined : statusFilter), [statusFilter]);
    const { sources, loading, error, refresh } = useAdminEventSources(statusParam);

    useEffect(() => {
        if (error) {
            toast.error(error);
        }
    }, [error]);

    useEffect(() => {
        let cancelled = false;
        const fetchMetrics = async () => {
            setMetricsLoading(true);
            try {
                const snapshot = await getEventMetricsAdmin();
                if (!cancelled) {
                    setMetrics(snapshot);
                }
            } catch (err: any) {
                if (!cancelled && err?.message) {
                    toast.error(err.message);
                }
            } finally {
                if (!cancelled) {
                    setMetricsLoading(false);
                }
            }
        };
        fetchMetrics();
        return () => {
            cancelled = true;
        };
    }, []);

    const formatTimestamp = (value?: string | null) => {
        if (!value) return "—";
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) {
            return value;
        }
        return date.toLocaleString();
    };

    const handleAddClick = () => {
        setEditingSource(null);
        setDialogOpen(true);
    };

    const handleEdit = (source: EventSourceDTO) => {
        setEditingSource(source);
        setDialogOpen(true);
    };

    const handleSave = async (values: EventSourceFormValues) => {
        setSaving(true);
        try {
            if (editingSource) {
                await updateEventSourceAdmin(editingSource.id, values);
                toast.success(`Updated ${values.name}`);
            } else {
                await createEventSourceAdmin(values);
                toast.success(`Created ${values.name}`);
            }
            await refresh(statusParam);
            setDialogOpen(false);
            setEditingSource(null);
        } catch (err: any) {
            toast.error(err?.message || "Failed to save event source");
        } finally {
            setSaving(false);
        }
    };

    const handleToggleStatus = async (source: EventSourceDTO) => {
        try {
            await toggleEventSourceStatusAdmin(source.id);
            const label = source.status === "active" ? "disabled" : "activated";
            toast.success(`${source.name} ${label}`);
            await refresh(statusParam);
        } catch (err: any) {
            toast.error(err?.message || "Failed to toggle source status");
        }
    };

    return (
        <div className="p-6 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-semibold">Event Sources</h1>
                    <p className="text-sm text-muted-foreground">
                        Manage websites, selectors, and scrape intervals for diaspora events.
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    <div className="flex flex-col text-sm">
                        <Label htmlFor="event-source-status" className="text-xs uppercase text-muted-foreground">
                            Status
                        </Label>
                        <select
                            id="event-source-status"
                            className="rounded-md border border-input bg-transparent px-3 py-2 text-sm"
                            value={statusFilter}
                            onChange={(e) => setStatusFilter(e.target.value as "all" | "active" | "disabled")}
                            disabled={loading}
                        >
                            <option value="all">All</option>
                            <option value="active">Active</option>
                            <option value="disabled">Disabled</option>
                        </select>
                    </div>
                    <Button onClick={handleAddClick}>Add Source</Button>
                </div>
            </div>

            <Card>
                <CardHeader className="pb-2">
                    <CardTitle className="text-base font-semibold">Event ingest snapshot</CardTitle>
                    <p className="text-sm text-muted-foreground">Latest totals from EventScraperBot.</p>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="flex flex-wrap gap-6">
                        <div>
                            <p className="text-xs uppercase text-muted-foreground">Events last 30 days</p>
                            <p className="text-2xl font-semibold">
                                {metrics ? metrics.total_events_last_30d.toLocaleString() : metricsLoading ? "…" : "—"}
                            </p>
                        </div>
                        <div className="flex-1 min-w-[240px]">
                            <p className="text-xs uppercase text-muted-foreground">Top sources (24h)</p>
                            <div className="mt-2 space-y-2">
                                {(metrics?.sources ?? []).slice(0, 4).map((stat) => (
                                    <div key={stat.source_id} className="flex items-center justify-between text-sm">
                                        <div>
                                            <p className="font-medium text-foreground">{stat.source_name}</p>
                                            <p className="text-xs text-muted-foreground">
                                                {stat.events_last_24h} events · last success {formatTimestamp(stat.last_success_at)}
                                            </p>
                                        </div>
                                        <span className="text-sm font-semibold">{stat.events_last_24h}</span>
                                    </div>
                                ))}
                                {!metricsLoading && (metrics?.sources?.length ?? 0) === 0 && (
                                    <p className="text-sm text-muted-foreground">No events ingested yet.</p>
                                )}
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>

            <EventSourceList
                sources={sources}
                loading={loading}
                onEdit={handleEdit}
                onToggleStatus={handleToggleStatus}
            />

            <EventSourceFormDialog
                open={dialogOpen}
                onOpenChange={setDialogOpen}
                initialSource={editingSource ?? undefined}
                onSubmit={handleSave}
                loading={saving}
            />
        </div>
    );
}


