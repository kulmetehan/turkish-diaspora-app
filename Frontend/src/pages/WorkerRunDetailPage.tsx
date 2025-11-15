import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Icon } from "@/components/Icon";
import { getWorkerRunDetail, type WorkerRunDetail } from "@/lib/apiAdmin";
import { cn } from "@/lib/ui/cn";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

// Status badge color mapping
const RUN_STATUS_BADGE_CLASSES: Record<string, string> = {
    pending: "bg-amber-100 text-amber-800 border-amber-200",
    running: "bg-blue-100 text-blue-800 border-blue-200",
    finished: "bg-emerald-100 text-emerald-800 border-emerald-200",
    failed: "bg-red-100 text-red-800 border-red-200",
};

// Helper functions
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

function formatDurationSeconds(value: number | null | undefined): string {
    if (!value || value <= 0) {
        return "–";
    }
    const totalSeconds = Math.round(value);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    const parts: string[] = [];
    if (hours) parts.push(`${hours}h`);
    if (minutes) parts.push(`${minutes}m`);
    if (!hours && !minutes) {
        parts.push(`${seconds}s`);
    } else if (seconds && parts.length < 2) {
        parts.push(`${seconds}s`);
    }
    return parts.join(" ");
}

function formatBotName(bot: string): string {
    return bot
        .replace(/_/g, " ")
        .replace(/\b\w/g, (char) => char.toUpperCase());
}

// State type
type RunDetailState =
    | { status: "idle" | "loading" | "success"; run?: WorkerRunDetail }
    | { status: "error"; errorMessage: string; notFound?: boolean };

export default function WorkerRunDetailPage() {
    const { runId } = useParams<{ runId: string }>();
    const [state, setState] = useState<RunDetailState>({ status: "loading" });

    useEffect(() => {
        if (!runId) {
            setState({
                status: "error",
                errorMessage: "No run id provided",
                notFound: false,
            });
            return;
        }

        const fetchRun = async () => {
            setState({ status: "loading" });
            try {
                const run = await getWorkerRunDetail(runId);
                setState({ status: "success", run });
            } catch (err: any) {
                const errorMessage = err?.message || "Failed to load worker run";
                const isNotFound = errorMessage.includes("404") || errorMessage.includes("not found");
                setState({
                    status: "error",
                    errorMessage,
                    notFound: isNotFound,
                });
            }
        };

        fetchRun();
    }, [runId]);

    // No run ID provided
    if (!runId) {
        return (
            <div className="p-6 max-w-5xl mx-auto">
                <Card className="rounded-2xl shadow-sm">
                    <CardHeader>
                        <CardTitle>Error</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <p className="text-sm text-muted-foreground mb-4">No run id provided.</p>
                        <Button variant="outline" asChild>
                            <Link to="/admin/workers">Back to Workers</Link>
                        </Button>
                    </CardContent>
                </Card>
            </div>
        );
    }

    // Loading state
    if (state.status === "loading") {
        return (
            <div className="p-6 space-y-6 max-w-5xl mx-auto">
                <Card className="rounded-2xl shadow-sm">
                    <CardHeader>
                        <Skeleton className="h-6 w-48" />
                        <Skeleton className="h-4 w-32 mt-2" />
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-4">
                            <Skeleton className="h-4 w-full" />
                            <Skeleton className="h-4 w-3/4" />
                            <Skeleton className="h-4 w-1/2" />
                        </div>
                    </CardContent>
                </Card>
                <Card className="rounded-2xl shadow-sm">
                    <CardHeader>
                        <Skeleton className="h-6 w-32" />
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-2">
                            <Skeleton className="h-4 w-full" />
                            <Skeleton className="h-4 w-full" />
                            <Skeleton className="h-4 w-3/4" />
                        </div>
                    </CardContent>
                </Card>
            </div>
        );
    }

    // Error state
    if (state.status === "error") {
        return (
            <div className="p-6 max-w-5xl mx-auto">
                <Card className="rounded-2xl shadow-sm">
                    <CardHeader>
                        <CardTitle>
                            {state.notFound ? "Worker run not found" : "Error loading worker run"}
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <p className="text-sm text-muted-foreground mb-4">
                            {state.notFound
                                ? `We couldn't find a worker run with id ${runId.substring(0, 8)}...`
                                : state.errorMessage}
                        </p>
                        <div className="flex gap-2">
                            <Button variant="outline" asChild>
                                <Link to="/admin/workers">Back to Workers</Link>
                            </Button>
                            {!state.notFound && (
                                <Button
                                    variant="default"
                                    onClick={() => {
                                        setState({ status: "loading" });
                                        getWorkerRunDetail(runId)
                                            .then((run) => setState({ status: "success", run }))
                                            .catch((err: any) =>
                                                setState({
                                                    status: "error",
                                                    errorMessage: err?.message || "Failed to load worker run",
                                                    notFound: err?.message?.includes("404") || err?.message?.includes("not found"),
                                                })
                                            );
                                    }}
                                >
                                    Retry
                                </Button>
                            )}
                        </div>
                    </CardContent>
                </Card>
            </div>
        );
    }

    // Success state
    const run = state.run!;
    const statusBadgeClass = RUN_STATUS_BADGE_CLASSES[run.status] || RUN_STATUS_BADGE_CLASSES.pending;
    const truncatedId = run.id.length > 8 ? `${run.id.substring(0, 8)}...` : run.id;

    // Build parameters display
    const parameters = run.parameters || {};
    const hasParameters = Object.keys(parameters).length > 0;
    const fallbackParams: Record<string, unknown> = {};
    if (!hasParameters) {
        if (run.city) fallbackParams.city = run.city;
        if (run.category) fallbackParams.category = run.category;
        if (run.counters) {
            if ("limit" in run.counters) fallbackParams.limit = run.counters.limit;
            if ("min_confidence" in run.counters) fallbackParams.min_confidence = run.counters.min_confidence;
            if ("model" in run.counters) fallbackParams.model = run.counters.model;
        }
    }
    const displayParams = hasParameters ? parameters : fallbackParams;

    // Build counters display (only show keys that exist)
    const counters = run.counters || {};
    const counterKeys = Object.keys(counters).filter((key) => counters[key] !== null && counters[key] !== undefined);

    return (
        <div className="p-6 space-y-6 max-w-5xl mx-auto">
            {/* Header with back button */}
            <div className="flex items-center gap-3 pb-4 border-b">
                <Button variant="ghost" size="sm" asChild>
                    <Link to="/admin/workers" className="flex items-center gap-2">
                        <Icon name="ArrowLeft" className="h-4 w-4" />
                        Back to Workers
                    </Link>
                </Button>
            </div>

            {/* Title and status */}
            <div className="space-y-2">
                <div className="flex items-center gap-3">
                    <h1 className="text-2xl font-semibold">Worker Run</h1>
                    <Badge variant="outline" className={cn("text-xs font-medium px-2 py-1", statusBadgeClass)}>
                        {formatRunStatus(run.status)}
                    </Badge>
                </div>
                <div className="text-sm text-muted-foreground">
                    <span className="font-mono">{truncatedId}</span>
                    {run.bot && (
                        <>
                            {" • "}
                            {formatBotName(run.bot)}
                        </>
                    )}
                    {run.city && ` • ${run.city}`}
                    {run.category && ` • ${run.category}`}
                </div>
                {run.progress !== undefined && (
                    <div className="mt-3 space-y-1">
                        <Progress value={run.progress ?? 0} />
                        <div className="text-xs text-muted-foreground">{run.progress}% complete</div>
                    </div>
                )}
            </div>

            {/* Run Summary Card */}
            <Card className="rounded-2xl shadow-sm">
                <CardHeader>
                    <CardTitle>Run Summary</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="space-y-3">
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            <div>
                                <div className="text-sm font-medium text-muted-foreground">Bot</div>
                                <div className="text-sm">{formatBotName(run.bot)}</div>
                            </div>
                            {run.city && (
                                <div>
                                    <div className="text-sm font-medium text-muted-foreground">City</div>
                                    <div className="text-sm">{run.city}</div>
                                </div>
                            )}
                            {run.category && (
                                <div>
                                    <div className="text-sm font-medium text-muted-foreground">Category</div>
                                    <div className="text-sm">{run.category}</div>
                                </div>
                            )}
                            <div>
                                <div className="text-sm font-medium text-muted-foreground">Status</div>
                                <div className="text-sm">
                                    <Badge variant="outline" className={cn("text-xs", statusBadgeClass)}>
                                        {formatRunStatus(run.status)}
                                    </Badge>
                                </div>
                            </div>
                            {run.duration_seconds !== null && run.duration_seconds !== undefined && (
                                <div>
                                    <div className="text-sm font-medium text-muted-foreground">Duration</div>
                                    <div className="text-sm">{formatDurationSeconds(run.duration_seconds)}</div>
                                </div>
                            )}
                        </div>
                        <div className="pt-2 border-t">
                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
                                <div>
                                    <div className="font-medium text-muted-foreground">Created</div>
                                    <div>{formatStartedAt(run.created_at)}</div>
                                </div>
                                <div>
                                    <div className="font-medium text-muted-foreground">Started</div>
                                    <div>{formatStartedAt(run.started_at)}</div>
                                </div>
                                <div>
                                    <div className="font-medium text-muted-foreground">Finished</div>
                                    <div>{formatStartedAt(run.finished_at)}</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Parameters Card */}
            <Card className="rounded-2xl shadow-sm">
                <CardHeader>
                    <CardTitle>Parameters</CardTitle>
                </CardHeader>
                <CardContent>
                    {Object.keys(displayParams).length > 0 ? (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            {Object.entries(displayParams).map(([key, value]) => (
                                <div key={key}>
                                    <div className="text-sm font-medium text-muted-foreground capitalize">
                                        {key.replace(/_/g, " ")}
                                    </div>
                                    <div className="text-sm">
                                        {typeof value === "object" ? JSON.stringify(value) : String(value)}
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="text-sm text-muted-foreground">No parameters recorded for this run.</div>
                    )}
                </CardContent>
            </Card>

            {/* Execution Summary Card */}
            <Card className="rounded-2xl shadow-sm">
                <CardHeader>
                    <CardTitle>Execution Summary</CardTitle>
                </CardHeader>
                <CardContent>
                    {counterKeys.length > 0 ? (
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                            {counterKeys.map((key) => (
                                <div key={key}>
                                    <div className="text-sm font-medium text-muted-foreground capitalize">
                                        {key.replace(/_/g, " ")}
                                    </div>
                                    <div className="text-sm">
                                        {typeof counters[key] === "object"
                                            ? JSON.stringify(counters[key])
                                            : String(counters[key])}
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="text-sm text-muted-foreground">No execution metrics recorded for this run.</div>
                    )}
                </CardContent>
            </Card>

            {/* Diagnostics Card */}
            <Card className="rounded-2xl shadow-sm">
                <CardHeader>
                    <CardTitle>Diagnostics</CardTitle>
                </CardHeader>
                <CardContent>
                    {run.error_message ? (
                        <div className="space-y-2">
                            {run.status === "failed" && (
                                <p className="text-sm text-muted-foreground">
                                    This run ended in an error. Check the message below and consider re-running the
                                    worker.
                                </p>
                            )}
                            <pre className="font-mono text-sm text-red-800 bg-red-50 p-3 rounded border border-red-200 overflow-auto">
                                {run.error_message}
                            </pre>
                        </div>
                    ) : (
                        <div className="text-sm text-muted-foreground">
                            {run.status === "finished"
                                ? "This run completed without recorded errors."
                                : run.status === "running"
                                  ? "This run is still in progress; no error reported."
                                  : "No errors reported for this run."}
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Logs Card (Placeholder) */}
            <Card className="rounded-2xl shadow-sm">
                <CardHeader>
                    <CardTitle>Logs</CardTitle>
                </CardHeader>
                <CardContent className="max-h-64 overflow-auto">
                    <div className="text-sm text-muted-foreground">No logs recorded for this run.</div>
                </CardContent>
            </Card>
        </div>
    );
}

