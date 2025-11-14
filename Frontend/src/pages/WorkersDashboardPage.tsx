import WorkerCard from "@/components/admin/WorkerCard";
import RunWorkerDialog from "@/components/admin/RunWorkerDialog";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getMetricsSnapshot, type MetricsSnapshot } from "@/lib/api";
import { listWorkerRuns, runWorker, type RunWorkerResponse, type WorkerRunListItem } from "@/lib/apiAdmin";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

function formatRunStatus(value: string | undefined | null): string {
    if (!value) return "Unknown";
    const cleaned = value.toLowerCase().replace(/_/g, " ");
    return cleaned.replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatStartedAt(value: string | null | undefined): string {
    if (!value) return "Not started";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return value;
    }
    return date.toLocaleString();
}

export default function WorkersDashboardPage() {
    const [metricsData, setMetricsData] = useState<MetricsSnapshot | null>(null);
    const [runHistory, setRunHistory] = useState<WorkerRunListItem[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedBotForRun, setSelectedBotForRun] = useState<string | null>(null);
    const [pollIntervalMs, setPollIntervalMs] = useState<number>(60000);
    const isMountedRef = useRef(false);

    const loadMetrics = useCallback(async () => {
        try {
            const res = await getMetricsSnapshot();
            if (!isMountedRef.current) return;
            setMetricsData(res);
            setError(null);

            // Adjust polling interval based on active runs
            const hasActive = Array.isArray(res.currentRuns) && res.currentRuns.some((run) =>
                ["pending", "running"].includes(run.status)
            );
            setPollIntervalMs((prev) => {
                const desired = hasActive ? 5000 : 60000;
                return prev === desired ? prev : desired;
            });
        } catch (e: any) {
            if (!isMountedRef.current) return;
            setError(e?.message || "Failed to load metrics");
        } finally {
            if (!isMountedRef.current) return;
            setLoading(false);
        }
    }, []);

    const loadRunHistory = useCallback(async () => {
        try {
            const res = await listWorkerRuns({ limit: 10 });
            if (!isMountedRef.current) return;
            setRunHistory(res.items);
        } catch (e: any) {
            // Silently fail for run history, it's optional
            if (import.meta.env.DEV) {
                console.warn("Failed to load run history:", e);
            }
        }
    }, []);

    useEffect(() => {
        isMountedRef.current = true;
        return () => {
            isMountedRef.current = false;
        };
    }, []);

    useEffect(() => {
        loadMetrics();
        loadRunHistory();

        const intervalId = window.setInterval(() => {
            loadMetrics();
            loadRunHistory();
        }, pollIntervalMs);

        return () => {
            window.clearInterval(intervalId);
        };
    }, [loadMetrics, loadRunHistory, pollIntervalMs]);

    const handleRunClick = (botId: string) => {
        setSelectedBotForRun(botId);
    };

    const handleRunSuccess = async (response: RunWorkerResponse) => {
        // Refresh metrics after successful run
        await loadMetrics();
        await loadRunHistory();
        // Set polling to fast mode if tracking is available
        if (response.tracking_available !== false) {
            setPollIntervalMs(5000);
        }
    };

    const workers = metricsData?.workers ?? [];
    const activeRuns = metricsData?.currentRuns ?? [];

    if (error) {
        return (
            <div className="p-6">
                <Card className="rounded-2xl shadow-sm">
                    <CardHeader>
                        <CardTitle>Workers Dashboard</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="p-2 text-sm text-destructive">{error}</div>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="p-6 space-y-6">
            <header className="flex items-center justify-between">
                <h1 className="text-2xl font-semibold">Workers Dashboard</h1>
                <div className="text-xs text-muted-foreground">
                    Polling every {Math.round(pollIntervalMs / 1000)}s
                </div>
            </header>

            {/* Active Runs Section */}
            {activeRuns.length > 0 && (
                <Card className="rounded-2xl shadow-sm">
                    <CardHeader>
                        <CardTitle>Active Runs</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-3">
                            {activeRuns.map((run) => (
                                <div key={run.id} className="rounded-lg border p-3">
                                    <div className="flex items-center justify-between gap-2 text-sm">
                                        <span className="font-medium capitalize">{run.bot}</span>
                                        <span className="text-xs text-muted-foreground">
                                            {formatRunStatus(run.status)}
                                        </span>
                                    </div>
                                    <div className="mt-1 grid gap-1 text-xs text-muted-foreground sm:grid-cols-3">
                                        <div>City: {run.city ?? "—"}</div>
                                        <div>Category: {run.category ?? "—"}</div>
                                        <div>Started: {formatStartedAt(run.startedAt)}</div>
                                    </div>
                                    {run.progress !== undefined && (
                                        <div className="mt-2">
                                            <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                                                <div
                                                    className="h-full bg-primary transition-all"
                                                    style={{ width: `${run.progress}%` }}
                                                />
                                            </div>
                                            <div className="mt-1 text-xs text-muted-foreground">
                                                {run.progress}%
                                            </div>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Worker Status Cards */}
            <div>
                <h2 className="text-xl font-semibold mb-4">Worker Status</h2>
                {loading ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {[1, 2, 3, 4, 5].map((i) => (
                            <Card key={i} className="rounded-2xl shadow-sm">
                                <CardHeader>
                                    <Skeleton className="h-6 w-32" />
                                </CardHeader>
                                <CardContent>
                                    <div className="space-y-2">
                                        <Skeleton className="h-4 w-full" />
                                        <Skeleton className="h-4 w-3/4" />
                                        <Skeleton className="h-4 w-1/2" />
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                ) : workers.length === 0 ? (
                    <Card className="rounded-2xl shadow-sm">
                        <CardContent className="p-6">
                            <div className="text-sm text-muted-foreground">
                                No worker status available.
                            </div>
                        </CardContent>
                    </Card>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {workers.map((worker) => (
                            <WorkerCard
                                key={worker.id}
                                worker={worker}
                                onRunClick={handleRunClick}
                            />
                        ))}
                    </div>
                )}
            </div>

            {/* Recent Run History */}
            {runHistory.length > 0 && (
                <Card className="rounded-2xl shadow-sm">
                    <CardHeader>
                        <CardTitle>Recent Run History</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="border-b">
                                        <th className="text-left p-2">Bot</th>
                                        <th className="text-left p-2">City</th>
                                        <th className="text-left p-2">Category</th>
                                        <th className="text-left p-2">Status</th>
                                        <th className="text-left p-2">Progress</th>
                                        <th className="text-left p-2">Started</th>
                                        <th className="text-left p-2">Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {runHistory.map((run) => (
                                        <tr key={run.id} className="border-b">
                                            <td className="p-2 capitalize">{run.bot}</td>
                                            <td className="p-2">{run.city ?? "—"}</td>
                                            <td className="p-2">{run.category ?? "—"}</td>
                                            <td className="p-2">{formatRunStatus(run.status)}</td>
                                            <td className="p-2">{run.progress}%</td>
                                            <td className="p-2">{formatStartedAt(run.started_at)}</td>
                                            <td className="p-2">
                                                <Link
                                                    to={`/admin/workers/runs/${run.id}`}
                                                    className="text-primary hover:underline text-xs"
                                                >
                                                    View details
                                                </Link>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Run Worker Dialog */}
            {selectedBotForRun && (
                <RunWorkerDialog
                    open={!!selectedBotForRun}
                    onOpenChange={(open) => {
                        if (!open) setSelectedBotForRun(null);
                    }}
                    botId={selectedBotForRun}
                    onSuccess={handleRunSuccess}
                />
            )}
        </div>
    );
}

