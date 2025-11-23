import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { AdminEventCandidate } from "@/lib/apiAdmin";

const STATE_LABELS: Record<AdminEventCandidate["state"], string> = {
    candidate: "Candidate",
    verified: "Verified",
    published: "Published",
    rejected: "Rejected",
};

const STATE_BADGE_CLASSES: Record<AdminEventCandidate["state"], string> = {
    candidate: "bg-slate-100 text-slate-800 border-slate-200",
    verified: "bg-blue-100 text-blue-800 border-blue-200",
    published: "bg-emerald-100 text-emerald-800 border-emerald-200",
    rejected: "bg-red-100 text-red-800 border-red-200",
};

type AdminEventsTableProps = {
    events: AdminEventCandidate[];
    loading: boolean;
    actionPendingId: number | null;
    onVerify: (id: number) => void;
    onPublish: (id: number) => void;
    onReject: (id: number) => void;
    onInspectDuplicates?: (id: number) => void;
};

export function AdminEventsTable({
    events,
    loading,
    actionPendingId,
    onVerify,
    onPublish,
    onReject,
    onInspectDuplicates,
}: AdminEventsTableProps) {
    if (loading) {
        return (
            <Card className="rounded-2xl shadow-sm">
                <CardContent className="p-4 space-y-4">
                    {[...Array(4)].map((_, idx) => (
                        <Skeleton key={idx} className="h-12 w-full" />
                    ))}
                </CardContent>
            </Card>
        );
    }

    if (events.length === 0) {
        return (
            <Card className="rounded-2xl shadow-sm">
                <CardContent className="p-6 text-sm text-muted-foreground">
                    No events found for the selected filters.
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className="rounded-2xl shadow-sm overflow-x-auto">
            <CardContent className="p-0">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="border-b bg-muted/50 text-left text-xs uppercase tracking-wide text-muted-foreground">
                            <th className="px-4 py-3 min-w-[200px]">Title</th>
                            <th className="px-4 py-3">Source</th>
                            <th className="px-4 py-3">Start</th>
                            <th className="px-4 py-3">Duplicate Status</th>
                            <th className="px-4 py-3">State</th>
                            <th className="px-4 py-3">Updated</th>
                            <th className="px-4 py-3 text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {events.map((event) => {
                            const isBusy = actionPendingId === event.id;
                            const startDate = new Date(event.start_time_utc);
                            const updatedAt = new Date(event.updated_at);
                            const isDuplicate = Boolean(event.duplicate_of_id);
                            const duplicateScore =
                                typeof event.duplicate_score === "number"
                                    ? `${Math.round(event.duplicate_score * 100)}%`
                                    : null;
                            return (
                                <tr key={event.id} className="border-b last:border-b-0">
                                    <td className="px-4 py-3 align-top">
                                        <div className="font-medium text-foreground">{event.title}</div>
                                        {event.location_text && (
                                            <div className="text-xs text-muted-foreground">{event.location_text}</div>
                                        )}
                                    </td>
                                    <td className="px-4 py-3 align-top">
                                        <div className="text-sm">
                                            {event.source_name || event.source_key || "—"}
                                        </div>
                                    </td>
                                    <td className="px-4 py-3 align-top">
                                        {Number.isNaN(startDate.getTime())
                                            ? "—"
                                            : startDate.toLocaleString()}
                                    </td>
                                    <td className="px-4 py-3 align-top space-y-1">
                                        {isDuplicate ? (
                                            <>
                                                <Badge variant="destructive">Duplicate</Badge>
                                                <div className="text-xs text-muted-foreground">
                                                    Canonical #{event.duplicate_of_id}
                                                    {duplicateScore ? ` • score ${duplicateScore}` : ""}
                                                </div>
                                            </>
                                        ) : (
                                            <>
                                                <Badge variant="secondary">Canonical</Badge>
                                                {event.has_duplicates ? (
                                                    <Button
                                                        size="xs"
                                                        variant="ghost"
                                                        onClick={() => onInspectDuplicates?.(event.id)}
                                                    >
                                                        View duplicates
                                                    </Button>
                                                ) : (
                                                    <div className="text-xs text-muted-foreground">
                                                        No duplicates
                                                    </div>
                                                )}
                                            </>
                                        )}
                                    </td>
                                    <td className="px-4 py-3 align-top">
                                        <Badge
                                            variant="outline"
                                            className={STATE_BADGE_CLASSES[event.state]}
                                        >
                                            {STATE_LABELS[event.state]}
                                        </Badge>
                                    </td>
                                    <td className="px-4 py-3 align-top">
                                        {Number.isNaN(updatedAt.getTime())
                                            ? "—"
                                            : updatedAt.toLocaleString()}
                                    </td>
                                    <td className="px-4 py-3 align-top text-right space-x-2">
                                        {event.state === "candidate" && (
                                            <>
                                                <Button
                                                    size="sm"
                                                    variant="secondary"
                                                    disabled={isBusy}
                                                    onClick={() => onVerify(event.id)}
                                                >
                                                    Verify
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    variant="default"
                                                    disabled={isBusy}
                                                    onClick={() => onPublish(event.id)}
                                                >
                                                    Publish
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    variant="destructive"
                                                    disabled={isBusy}
                                                    onClick={() => onReject(event.id)}
                                                >
                                                    Reject
                                                </Button>
                                            </>
                                        )}
                                        {event.state === "verified" && (
                                            <>
                                                <Button
                                                    size="sm"
                                                    variant="default"
                                                    disabled={isBusy}
                                                    onClick={() => onPublish(event.id)}
                                                >
                                                    Publish
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    variant="destructive"
                                                    disabled={isBusy}
                                                    onClick={() => onReject(event.id)}
                                                >
                                                    Reject
                                                </Button>
                                            </>
                                        )}
                                        {event.state === "published" && (
                                            <Button
                                                size="sm"
                                                variant="destructive"
                                                disabled={isBusy}
                                                onClick={() => onReject(event.id)}
                                            >
                                                Reject
                                            </Button>
                                        )}
                                        {event.state === "rejected" && (
                                            <span className="text-xs text-muted-foreground">No actions</span>
                                        )}
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </CardContent>
        </Card>
    );
}


