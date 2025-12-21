import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import EventSourceFormDialog, { type EventSourceFormValues } from "@/components/admin/EventSourceFormDialog";
import EventSourceList from "@/components/admin/EventSourceList";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { useAdminEventSources } from "@/hooks/useAdminEventSources";
import {
    createEventSourceAdmin,
    deleteEventSourceAdmin,
    getEventMetricsAdmin,
    getEventSourceDiagnosticsAdmin,
    runWorker,
    toggleEventSourceStatusAdmin,
    updateEventSourceAdmin,
    type EventMetricsSnapshotDTO,
    type EventSourceDTO,
    type EventSourceDiagnostics,
} from "@/lib/apiAdmin";

export default function AdminEventSourcesPage() {
    const [statusFilter, setStatusFilter] = useState<"all" | "active" | "disabled">("all");
    const [dialogOpen, setDialogOpen] = useState(false);
    const [editingSource, setEditingSource] = useState<EventSourceDTO | null>(null);
    const [saving, setSaving] = useState(false);
    const [metrics, setMetrics] = useState<EventMetricsSnapshotDTO | null>(null);
    const [metricsLoading, setMetricsLoading] = useState(false);
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [deletingSource, setDeletingSource] = useState<EventSourceDTO | null>(null);
    const [deleting, setDeleting] = useState(false);
    const [cascadeDelete, setCascadeDelete] = useState(false);
    const [diagnosticsDialogOpen, setDiagnosticsDialogOpen] = useState(false);
    const [diagnosticsSource, setDiagnosticsSource] = useState<EventSourceDTO | null>(null);
    const [diagnostics, setDiagnostics] = useState<EventSourceDiagnostics | null>(null);
    const [diagnosticsLoading, setDiagnosticsLoading] = useState(false);
    const [runningNormalization, setRunningNormalization] = useState(false);

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

    const handleDelete = (source: EventSourceDTO) => {
        setDeletingSource(source);
        setDeleteDialogOpen(true);
    };

    const handleConfirmDelete = async () => {
        if (!deletingSource) return;
        setDeleting(true);
        try {
            const result = await deleteEventSourceAdmin(deletingSource.id, cascadeDelete);
            toast.success(
                `Deleted ${deletingSource.name}${result.related_records_deleted > 0 ? ` (${result.related_records_deleted} related records deleted)` : ""}`
            );
            setDeleteDialogOpen(false);
            setDeletingSource(null);
            setCascadeDelete(false);
            await refresh(statusParam);
        } catch (err: any) {
            toast.error(err?.message || "Failed to delete event source");
        } finally {
            setDeleting(false);
        }
    };

    const handleDiagnostics = async (source: EventSourceDTO) => {
        setDiagnosticsSource(source);
        setDiagnosticsDialogOpen(true);
        setDiagnosticsLoading(true);
        try {
            const data = await getEventSourceDiagnosticsAdmin(source.id);
            setDiagnostics(data);
        } catch (err: any) {
            toast.error(err?.message || "Failed to load diagnostics");
            setDiagnosticsDialogOpen(false);
        } finally {
            setDiagnosticsLoading(false);
        }
    };

    const handleRunNormalization = async () => {
        setRunningNormalization(true);
        try {
            const result = await runWorker({ bot: "event_normalization", max_jobs: 200 });
            toast.success(`Normalization bot started (run ID: ${result.run_id?.slice(0, 8)}...)`);
            // Refresh diagnostics after a short delay
            setTimeout(async () => {
                if (diagnosticsSource) {
                    const data = await getEventSourceDiagnosticsAdmin(diagnosticsSource.id);
                    setDiagnostics(data);
                }
            }, 2000);
        } catch (err: any) {
            toast.error(err?.message || "Failed to start normalization bot");
        } finally {
            setRunningNormalization(false);
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
                onDelete={handleDelete}
                onDiagnostics={handleDiagnostics}
            />

            <EventSourceFormDialog
                open={dialogOpen}
                onOpenChange={setDialogOpen}
                initialSource={editingSource ?? undefined}
                onSubmit={handleSave}
                loading={saving}
            />

            <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Delete Event Source</DialogTitle>
                        <DialogDescription>
                            {deletingSource && (
                                <>
                                    Are you sure you want to delete <strong>{deletingSource.name}</strong>?
                                    {cascadeDelete && (
                                        <span className="block mt-2 text-amber-600">
                                            This will also delete all related events, pages, and candidates from this source.
                                        </span>
                                    )}
                                </>
                            )}
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4">
                        <div className="flex items-center space-x-2">
                            <input
                                type="checkbox"
                                id="cascade-delete"
                                checked={cascadeDelete}
                                onChange={(e) => setCascadeDelete(e.target.checked)}
                                className="rounded border-gray-300"
                            />
                            <label htmlFor="cascade-delete" className="text-sm">
                                Delete related records (events, pages, candidates)
                            </label>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => {
                                setDeleteDialogOpen(false);
                                setDeletingSource(null);
                                setCascadeDelete(false);
                            }}
                            disabled={deleting}
                        >
                            Cancel
                        </Button>
                        <Button variant="destructive" onClick={handleConfirmDelete} disabled={deleting}>
                            {deleting ? "Deleting..." : "Delete"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <Dialog open={diagnosticsDialogOpen} onOpenChange={setDiagnosticsDialogOpen}>
                <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle>
                            Diagnostics: {diagnosticsSource?.name || "Event Source"}
                        </DialogTitle>
                        <DialogDescription>
                            Pipeline status and event counts for this source
                        </DialogDescription>
                    </DialogHeader>
                    {diagnosticsLoading ? (
                        <div className="p-4 text-sm text-muted-foreground">Loading diagnostics...</div>
                    ) : diagnostics ? (
                        <div className="space-y-6">
                            {/* Source Info */}
                            <div className="space-y-2">
                                <h3 className="text-sm font-semibold">Source Information</h3>
                                <div className="grid grid-cols-2 gap-4 text-sm">
                                    <div>
                                        <span className="text-muted-foreground">Status:</span>{" "}
                                        <span className={diagnostics.status === "active" ? "text-emerald-600" : "text-gray-600"}>
                                            {diagnostics.status}
                                        </span>
                                    </div>
                                    <div>
                                        <span className="text-muted-foreground">Last Run:</span>{" "}
                                        {diagnostics.last_run_at ? new Date(diagnostics.last_run_at).toLocaleString() : "Never"}
                                    </div>
                                    <div>
                                        <span className="text-muted-foreground">Last Success:</span>{" "}
                                        {diagnostics.last_success_at ? new Date(diagnostics.last_success_at).toLocaleString() : "Never"}
                                    </div>
                                    {diagnostics.last_error && (
                                        <div className="col-span-2">
                                            <span className="text-muted-foreground">Last Error:</span>{" "}
                                            <span className="text-red-600">{diagnostics.last_error}</span>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Pages Pipeline */}
                            <div className="space-y-2">
                                <h3 className="text-sm font-semibold">Pages Pipeline</h3>
                                <div className="grid grid-cols-4 gap-4 text-sm">
                                    <div>
                                        <div className="text-muted-foreground">Total</div>
                                        <div className="text-lg font-semibold">{diagnostics.pages_raw_count}</div>
                                    </div>
                                    <div>
                                        <div className="text-muted-foreground">Pending</div>
                                        <div className="text-lg font-semibold text-amber-600">{diagnostics.pages_pending}</div>
                                    </div>
                                    <div>
                                        <div className="text-muted-foreground">Extracted</div>
                                        <div className="text-lg font-semibold text-emerald-600">{diagnostics.pages_extracted}</div>
                                    </div>
                                    <div>
                                        <div className="text-muted-foreground">Errors</div>
                                        <div className="text-lg font-semibold text-red-600">{diagnostics.pages_error}</div>
                                    </div>
                                </div>
                            </div>

                            {/* Events Raw Pipeline */}
                            <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                    <h3 className="text-sm font-semibold">Events Raw Pipeline</h3>
                                    {diagnostics.events_raw_pending > 0 && (
                                        <Button
                                            size="sm"
                                            variant="default"
                                            onClick={handleRunNormalization}
                                            disabled={runningNormalization}
                                        >
                                            {runningNormalization ? "Running..." : `Normalize ${diagnostics.events_raw_pending} Events`}
                                        </Button>
                                    )}
                                </div>
                                <div className="grid grid-cols-4 gap-4 text-sm">
                                    <div>
                                        <div className="text-muted-foreground">Total</div>
                                        <div className="text-lg font-semibold">{diagnostics.events_raw_count}</div>
                                    </div>
                                    <div>
                                        <div className="text-muted-foreground">Pending</div>
                                        <div className="text-lg font-semibold text-amber-600">{diagnostics.events_raw_pending}</div>
                                    </div>
                                    <div>
                                        <div className="text-muted-foreground">Enriched</div>
                                        <div className="text-lg font-semibold text-emerald-600">{diagnostics.events_raw_enriched}</div>
                                    </div>
                                    <div>
                                        <div className="text-muted-foreground">Errors</div>
                                        <div className="text-lg font-semibold text-red-600">{diagnostics.events_raw_error}</div>
                                    </div>
                                </div>
                                {diagnostics.events_raw_pending > 0 && (
                                    <div className="rounded-lg bg-amber-50 border border-amber-200 p-3 text-xs text-amber-700">
                                        <strong>Note:</strong> {diagnostics.events_raw_pending} events are waiting to be normalized. 
                                        Click the button above to run the normalization bot, which will convert these events 
                                        from <code>event_raw</code> to <code>events_candidate</code> so they appear in the Events Dashboard.
                                    </div>
                                )}
                            </div>

                            {/* Events Candidate */}
                            <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                    <h3 className="text-sm font-semibold">Events Candidate</h3>
                                    {diagnostics.events_candidate_by_state.candidate > 0 && (
                                        <Button
                                            size="sm"
                                            variant="default"
                                            onClick={async () => {
                                                setRunningNormalization(true);
                                                try {
                                                    const result = await runWorker({ bot: "verify_events", max_jobs: 200 });
                                                    toast.success(`Event verification bot started (run ID: ${result.run_id?.slice(0, 8)}...)`);
                                                    setTimeout(async () => {
                                                        if (diagnosticsSource) {
                                                            const data = await getEventSourceDiagnosticsAdmin(diagnosticsSource.id);
                                                            setDiagnostics(data);
                                                        }
                                                    }, 2000);
                                                } catch (err: any) {
                                                    toast.error(err?.message || "Failed to start verification bot");
                                                } finally {
                                                    setRunningNormalization(false);
                                                }
                                            }}
                                            disabled={runningNormalization}
                                        >
                                            {runningNormalization ? "Running..." : `Verify ${diagnostics.events_candidate_by_state.candidate} Events`}
                                        </Button>
                                    )}
                                </div>
                                <div className="text-sm">
                                    <div className="mb-2">
                                        <span className="text-muted-foreground">Total:</span>{" "}
                                        <span className="text-lg font-semibold">{diagnostics.events_candidate_count}</span>
                                    </div>
                                    <div className="flex flex-wrap gap-2">
                                        {Object.entries(diagnostics.events_candidate_by_state).map(([state, count]) => (
                                            <div key={state} className="px-2 py-1 bg-muted rounded text-xs">
                                                {state}: {count}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                                {diagnostics.events_candidate_by_state.candidate > 0 && (
                                    <div className="rounded-lg bg-blue-50 border border-blue-200 p-3 text-xs text-blue-700">
                                        <strong>Note:</strong> {diagnostics.events_candidate_by_state.candidate} events are in "candidate" state waiting for AI classification. 
                                        Click the button above to run the verification bot, which will classify events and automatically 
                                        promote high-confidence Turkish events (≥80%) to "verified" state.
                                    </div>
                                )}
                            </div>

                            {/* Visibility */}
                            <div className="space-y-2">
                                <h3 className="text-sm font-semibold">Visibility</h3>
                                <div className="grid grid-cols-2 gap-4 text-sm">
                                    <div>
                                        <div className="text-muted-foreground">Published</div>
                                        <div className="text-lg font-semibold">{diagnostics.events_published_count}</div>
                                    </div>
                                    <div>
                                        <div className="text-muted-foreground">Visible on Frontend</div>
                                        <div className="text-lg font-semibold text-emerald-600">
                                            {diagnostics.events_visible_in_frontend}
                                        </div>
                                    </div>
                                </div>
                                {diagnostics.events_published_count > diagnostics.events_visible_in_frontend && (
                                    <div className="text-xs text-amber-600 mt-2">
                                        {diagnostics.events_published_count - diagnostics.events_visible_in_frontend} published events not visible
                                        (likely past events or filtered by country/location)
                                    </div>
                                )}
                            </div>
                        </div>
                    ) : (
                        <div className="p-4 text-sm text-muted-foreground">No diagnostics available</div>
                    )}
                </DialogContent>
            </Dialog>
        </div>
    );
}


