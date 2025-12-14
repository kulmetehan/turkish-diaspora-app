import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { AdminEventsTable } from "@/components/admin/AdminEventsTable";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAdminEventSources } from "@/hooks/useAdminEventSources";
import {
    flushAllEventsAdmin,
    getEventCandidateDuplicatesAdmin,
    listEventCandidatesAdmin,
    publishEventCandidateAdmin,
    rejectEventCandidateAdmin,
    verifyEventCandidateAdmin,
    type AdminEventCandidate,
    type AdminEventDuplicateCluster,
} from "@/lib/apiAdmin";

const STATE_FILTERS = [
    { value: "ALL", label: "All states" },
    { value: "candidate", label: "Candidate" },
    { value: "verified", label: "Verified" },
    { value: "published", label: "Published" },
    { value: "rejected", label: "Rejected" },
] as const;

const DEDUPE_FILTERS = [
    { value: "all", label: "All records" },
    { value: "canonical", label: "Canonical only" },
    { value: "duplicates", label: "Duplicates only" },
] as const;

const PAGE_SIZE = 25;

export default function AdminEventsPage() {
    const [stateFilter, setStateFilter] = useState<(typeof STATE_FILTERS)[number]["value"]>("ALL");
    const [sourceFilter, setSourceFilter] = useState<string>("ALL");
    const [search, setSearch] = useState<string>("");
    const [dedupeFilter, setDedupeFilter] = useState<(typeof DEDUPE_FILTERS)[number]["value"]>("all");
    const [events, setEvents] = useState<AdminEventCandidate[]>([]);
    const [loading, setLoading] = useState<boolean>(false);
    const [actionPendingId, setActionPendingId] = useState<number | null>(null);
    const [offset, setOffset] = useState<number>(0);
    const [total, setTotal] = useState<number>(0);
    const [duplicatesDialogOpen, setDuplicatesDialogOpen] = useState<boolean>(false);
    const [duplicateCluster, setDuplicateCluster] = useState<AdminEventDuplicateCluster | null>(null);
    const [duplicatesLoading, setDuplicatesLoading] = useState<boolean>(false);
    const [flushDialogOpen, setFlushDialogOpen] = useState<boolean>(false);
    const [flushing, setFlushing] = useState<boolean>(false);
    const { sources } = useAdminEventSources();

    const selectedSourceLabel = useMemo(() => {
        if (sourceFilter === "ALL") return "All sources";
        const match = sources.find((s) => s.key === sourceFilter);
        return match?.name ?? sourceFilter;
    }, [sourceFilter, sources]);

    useEffect(() => {
        setOffset(0);
    }, [stateFilter, sourceFilter, search, dedupeFilter]);

    useEffect(() => {
        let cancelled = false;
        const fetchEvents = async () => {
            setLoading(true);
            try {
                const response = await listEventCandidatesAdmin({
                    state: stateFilter === "ALL" ? undefined : (stateFilter as AdminEventCandidate["state"]),
                    sourceKey: sourceFilter === "ALL" ? undefined : sourceFilter,
                    search: search.trim() || undefined,
                    duplicatesOnly: dedupeFilter === "duplicates",
                    canonicalOnly: dedupeFilter === "canonical",
                    limit: PAGE_SIZE,
                    offset,
                });
                if (cancelled) return;
                setEvents(response.items);
                setTotal(response.total);
            } catch (err: any) {
                if (!cancelled) {
                    toast.error(err?.message || "Failed to load events");
                }
            } finally {
                if (!cancelled) {
                    setLoading(false);
                }
            }
        };
        fetchEvents();
        return () => {
            cancelled = true;
        };
    }, [stateFilter, sourceFilter, search, dedupeFilter, offset]);

    const refetch = async () => {
        try {
            const response = await listEventCandidatesAdmin({
                state: stateFilter === "ALL" ? undefined : (stateFilter as AdminEventCandidate["state"]),
                sourceKey: sourceFilter === "ALL" ? undefined : sourceFilter,
                search: search.trim() || undefined,
                duplicatesOnly: dedupeFilter === "duplicates",
                canonicalOnly: dedupeFilter === "canonical",
                limit: PAGE_SIZE,
                offset,
            });
            setEvents(response.items);
            setTotal(response.total);
        } catch (err: any) {
            toast.error(err?.message || "Failed to refresh events");
        }
    };

    const handleAction = async (
        id: number,
        action: "verify" | "publish" | "reject",
    ) => {
        setActionPendingId(id);
        try {
            if (action === "verify") {
                await verifyEventCandidateAdmin(id);
                toast.success("Event verified");
            } else if (action === "publish") {
                await publishEventCandidateAdmin(id);
                toast.success("Event published");
            } else {
                await rejectEventCandidateAdmin(id);
                toast.success("Event rejected");
            }
            await refetch();
        } catch (err: any) {
            toast.error(err?.message || `Failed to ${action} event`);
        } finally {
            setActionPendingId(null);
        }
    };

    const handleInspectDuplicates = async (id: number) => {
        setDuplicatesDialogOpen(true);
        setDuplicatesLoading(true);
        try {
            const cluster = await getEventCandidateDuplicatesAdmin(id);
            setDuplicateCluster(cluster);
        } catch (err: any) {
            toast.error(err?.message || "Failed to load duplicates");
            setDuplicatesDialogOpen(false);
        } finally {
            setDuplicatesLoading(false);
        }
    };

    const resetDuplicatesDialog = (open: boolean) => {
        setDuplicatesDialogOpen(open);
        if (!open) {
            setDuplicateCluster(null);
            setDuplicatesLoading(false);
        }
    };

    const handleFlush = async () => {
        setFlushing(true);
        try {
            const result = await flushAllEventsAdmin(true);
            toast.success(result.message || "Events flushed successfully");
            setFlushDialogOpen(false);
            await refetch();
        } catch (err: any) {
            toast.error(err?.message || "Failed to flush events");
        } finally {
            setFlushing(false);
        }
    };

    const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
    const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

    return (
        <div className="p-6 space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-semibold">Events Dashboard</h1>
                    <p className="text-sm text-muted-foreground">
                        Review candidate events and promote them through the verification workflow.
                    </p>
                </div>
                <Button
                    variant="destructive"
                    onClick={() => setFlushDialogOpen(true)}
                >
                    Flush All Events
                </Button>
            </div>

            <Card className="rounded-2xl shadow-sm">
                <CardContent className="p-4 space-y-4">
                    <div className="grid gap-4 md:grid-cols-4">
                        <div className="space-y-2">
                            <Label htmlFor="state-filter">Status</Label>
                            <Select
                                value={stateFilter}
                                onValueChange={(value) =>
                                    setStateFilter(value as (typeof STATE_FILTERS)[number]["value"])
                                }
                            >
                                <SelectTrigger id="state-filter">
                                    <SelectValue placeholder="All states" />
                                </SelectTrigger>
                                <SelectContent>
                                    {STATE_FILTERS.map((option) => (
                                        <SelectItem key={option.value} value={option.value}>
                                            {option.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="source-filter">Source</Label>
                            <Select
                                value={sourceFilter}
                                onValueChange={(value) => setSourceFilter(value)}
                            >
                                <SelectTrigger id="source-filter">
                                    <SelectValue placeholder="All sources">
                                        {selectedSourceLabel}
                                    </SelectValue>
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="ALL">All sources</SelectItem>
                                    {sources.map((source) => (
                                        <SelectItem key={source.id} value={source.key}>
                                            {source.name}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="duplicate-filter">Duplicates</Label>
                            <Select
                                value={dedupeFilter}
                                onValueChange={(value) =>
                                    setDedupeFilter(value as (typeof DEDUPE_FILTERS)[number]["value"])
                                }
                            >
                                <SelectTrigger id="duplicate-filter">
                                    <SelectValue placeholder="All records" />
                                </SelectTrigger>
                                <SelectContent>
                                    {DEDUPE_FILTERS.map((option) => (
                                        <SelectItem key={option.value} value={option.value}>
                                            {option.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="event-search">Search</Label>
                            <Input
                                id="event-search"
                                placeholder="Search title or description"
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                            />
                        </div>
                    </div>

                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <span>
                            Showing {events.length} of {total} events
                        </span>
                        <span>
                            Page {currentPage} / {pageCount}
                        </span>
                    </div>
                </CardContent>
            </Card>

            <AdminEventsTable
                events={events}
                loading={loading}
                actionPendingId={actionPendingId}
                onVerify={(id) => handleAction(id, "verify")}
                onPublish={(id) => handleAction(id, "publish")}
                onReject={(id) => handleAction(id, "reject")}
                onInspectDuplicates={handleInspectDuplicates}
            />

            <div className="flex items-center justify-between">
                <Button
                    variant="outline"
                    disabled={offset === 0 || loading}
                    onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                >
                    Previous
                </Button>
                <Button
                    variant="outline"
                    disabled={offset + PAGE_SIZE >= total || loading}
                    onClick={() => setOffset(offset + PAGE_SIZE)}
                >
                    Next
                </Button>
            </div>

            <Dialog open={flushDialogOpen} onOpenChange={setFlushDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Flush All Events</DialogTitle>
                        <DialogDescription>
                            This will delete all events from the database (events_candidate and event_raw tables).
                            The events_public view will automatically be empty. Event sources will be reset so
                            the scraper can run immediately. This action cannot be undone.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="flex justify-end gap-2">
                        <Button
                            variant="outline"
                            onClick={() => setFlushDialogOpen(false)}
                            disabled={flushing}
                        >
                            Cancel
                        </Button>
                        <Button
                            variant="destructive"
                            onClick={handleFlush}
                            disabled={flushing}
                        >
                            {flushing ? "Flushing..." : "Confirm Flush"}
                        </Button>
                    </div>
                </DialogContent>
            </Dialog>

            <Dialog open={duplicatesDialogOpen} onOpenChange={resetDuplicatesDialog}>
                <DialogContent className="max-w-2xl">
                    <DialogHeader>
                        <DialogTitle>Duplicate cluster</DialogTitle>
                        <DialogDescription>Canonical event with its merged duplicates.</DialogDescription>
                    </DialogHeader>
                    {duplicatesLoading && <p className="text-sm text-muted-foreground">Loading duplicates…</p>}
                    {!duplicatesLoading && duplicateCluster && (
                        <div className="space-y-4">
                            <div>
                                <p className="text-xs font-semibold uppercase text-muted-foreground mb-1">Canonical</p>
                                <div className="space-y-1 rounded-lg border p-3">
                                    <div className="font-medium">{duplicateCluster.canonical.title}</div>
                                    <div className="text-xs text-muted-foreground">
                                        Source: {duplicateCluster.canonical.source_name || duplicateCluster.canonical.source_key}
                                    </div>
                                    <div className="text-xs text-muted-foreground">
                                        Start: {new Date(duplicateCluster.canonical.start_time_utc).toLocaleDateString()}
                                    </div>
                                    {duplicateCluster.canonical.location_text && (
                                        <div className="text-xs text-muted-foreground">
                                            Location: {duplicateCluster.canonical.location_text}
                                        </div>
                                    )}
                                </div>
                            </div>
                            <div>
                                <p className="text-xs font-semibold uppercase text-muted-foreground mb-1">
                                    Duplicates ({duplicateCluster.duplicates.length})
                                </p>
                                {duplicateCluster.duplicates.length === 0 ? (
                                    <p className="text-xs text-muted-foreground">No duplicates recorded.</p>
                                ) : (
                                    <div className="space-y-3">
                                        {duplicateCluster.duplicates.map((dup) => (
                                            <div key={dup.id} className="rounded-lg border p-3 space-y-1">
                                                <div className="font-medium">{dup.title}</div>
                                                <div className="text-xs text-muted-foreground">
                                                    Source: {dup.source_name || dup.source_key}
                                                </div>
                                                <div className="text-xs text-muted-foreground">
                                                    Start: {new Date(dup.start_time_utc).toLocaleDateString()}
                                                </div>
                                                {dup.location_text && (
                                                    <div className="text-xs text-muted-foreground">
                                                        Location: {dup.location_text}
                                                    </div>
                                                )}
                                                {typeof dup.duplicate_score === "number" && (
                                                    <div className="text-xs text-muted-foreground">
                                                        Similarity score: {Math.round(dup.duplicate_score * 100)}%
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                    {!duplicatesLoading && !duplicateCluster && (
                        <p className="text-sm text-muted-foreground">Select a canonical event to inspect duplicates.</p>
                    )}
                </DialogContent>
            </Dialog>
        </div>
    );
}


