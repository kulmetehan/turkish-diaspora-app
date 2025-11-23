import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { EventSourceDTO } from "@/lib/apiAdmin";

function formatTimestamp(value?: string | null): string {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString();
}

type EventSourceListProps = {
    sources: EventSourceDTO[];
    loading: boolean;
    onEdit: (source: EventSourceDTO) => void;
    onToggleStatus: (source: EventSourceDTO) => void;
};

function StatusBadge({ status }: { status: EventSourceDTO["status"] }) {
    const variant = status === "active" ? "success" : "secondary";
    const label = status === "active" ? "Active" : "Disabled";
    return (
        <Badge variant={variant === "success" ? "default" : "outline"} className={status === "active" ? "bg-emerald-600 hover:bg-emerald-700" : ""}>
            {label}
        </Badge>
    );
}

export default function EventSourceList({ sources, loading, onEdit, onToggleStatus }: EventSourceListProps) {
    return (
        <Card className="rounded-2xl shadow-sm">
            <CardContent className="p-0">
                {loading ? (
                    <div className="space-y-2 p-4">
                        {[...Array(3)].map((_, index) => (
                            <Skeleton key={index} className="h-12 w-full" />
                        ))}
                    </div>
                ) : sources.length === 0 ? (
                    <div className="p-6 text-sm text-muted-foreground">
                        No event sources yet. Add your first website to start scraping events.
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b bg-muted/50 text-left text-xs uppercase tracking-wide text-muted-foreground">
                                    <th className="px-4 py-3">Name</th>
                                    <th className="px-4 py-3">Key</th>
                                    <th className="px-4 py-3">Base URL</th>
                                    <th className="px-4 py-3">Interval</th>
                                    <th className="px-4 py-3">Status</th>
                                    <th className="px-4 py-3">Last success</th>
                                    <th className="px-4 py-3">Last error</th>
                                    <th className="px-4 py-3 text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {sources.map((source) => (
                                    <tr key={source.id} className="border-b last:border-0">
                                        <td className="px-4 py-3 font-medium text-foreground">{source.name}</td>
                                        <td className="px-4 py-3 text-muted-foreground">{source.key}</td>
                                        <td className="px-4 py-3">
                                            <a href={source.list_url ?? source.base_url} target="_blank" rel="noreferrer" className="text-primary hover:underline break-all">
                                                {source.list_url ?? source.base_url}
                                            </a>
                                        </td>
                                        <td className="px-4 py-3">{source.interval_minutes} min</td>
                                        <td className="px-4 py-3">
                                            <StatusBadge status={source.status} />
                                        </td>
                                        <td className="px-4 py-3 text-muted-foreground">{formatTimestamp(source.last_success_at)}</td>
                                        <td className="px-4 py-3 text-xs text-muted-foreground max-w-xs">
                                            {source.last_error ? source.last_error.slice(0, 120) : "—"}
                                        </td>
                                        <td className="px-4 py-3 text-right space-x-2">
                                            <Button size="sm" variant="outline" onClick={() => onEdit(source)}>
                                                Edit
                                            </Button>
                                            <Button
                                                size="sm"
                                                variant={source.status === "active" ? "destructive" : "default"}
                                                onClick={() => onToggleStatus(source)}
                                            >
                                                {source.status === "active" ? "Disable" : "Activate"}
                                            </Button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}


