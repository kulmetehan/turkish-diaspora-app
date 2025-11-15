import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { listAILogs, type AILogItem } from "@/lib/apiAdmin";
import { toast } from "sonner";
import { Icon } from "@/components/Icon";

type Props = {
    locationId: number;
};

const PAGE_SIZE = 20;

export default function AIDecisionsTab({ locationId }: Props) {
    const [logs, setLogs] = useState<AILogItem[]>([]);
    const [loading, setLoading] = useState(false);
    const [total, setTotal] = useState(0);
    const [offset, setOffset] = useState(0);

    useEffect(() => {
        if (!locationId) return;
        
        let active = true;
        setLoading(true);
        
        listAILogs({
            location_id: locationId,
            limit: PAGE_SIZE,
            offset,
        })
            .then((response) => {
                if (!active) return;
                setLogs(response.items);
                setTotal(response.total);
            })
            .catch((error) => {
                if (!active) return;
                toast.error(error?.message || "Failed to load AI decisions");
                console.error("Failed to load AI logs:", error);
            })
            .finally(() => {
                if (active) setLoading(false);
            });

        return () => {
            active = false;
        };
    }, [locationId, offset]);

    const formatDate = (dateString: string) => {
        try {
            const date = new Date(dateString);
            return date.toLocaleString(undefined, {
                year: "numeric",
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
            });
        } catch {
            return dateString;
        }
    };

    const formatActionType = (actionType: string) => {
        // Clean up action type for display
        return actionType
            .split(".")
            .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
            .join(" ");
    };

    const getConfidenceColor = (confidence?: number | null) => {
        if (confidence == null) return "bg-gray-200";
        if (confidence >= 0.8) return "bg-green-500";
        if (confidence >= 0.6) return "bg-yellow-500";
        return "bg-red-500";
    };

    const page = Math.floor(offset / PAGE_SIZE) + 1;
    const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
    const hasPrev = offset > 0;
    const hasNext = offset + PAGE_SIZE < total;

    if (loading && logs.length === 0) {
        return (
            <div className="py-8 text-center text-muted-foreground">
                Loading AI decisions...
            </div>
        );
    }

    if (logs.length === 0 && !loading) {
        return (
            <div className="py-8 text-center text-muted-foreground">
                No AI decisions found for this location.
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                    Showing {logs.length} of {total} decisions
                </p>
                <div className="flex items-center gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                        disabled={!hasPrev || loading}
                    >
                        <Icon name="ChevronLeft" className="h-4 w-4" />
                        Previous
                    </Button>
                    <span className="text-sm text-muted-foreground">
                        Page {page} of {pageCount}
                    </span>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setOffset(offset + PAGE_SIZE)}
                        disabled={!hasNext || loading}
                    >
                        Next
                        <Icon name="ChevronRight" className="h-4 w-4" />
                    </Button>
                </div>
            </div>

            <div className="space-y-3">
                {logs.map((log) => (
                    <Card key={log.id} className={!log.is_success ? "border-red-300 bg-red-50/50" : ""}>
                        <CardContent className="p-4">
                            <div className="flex items-start justify-between gap-4">
                                <div className="flex-1 space-y-2">
                                    <div className="flex items-center gap-2 flex-wrap">
                                        {log.model_used && (
                                            <Badge variant="outline" className="text-xs">
                                                {log.model_used}
                                            </Badge>
                                        )}
                                        <Badge
                                            variant={log.is_success ? "secondary" : "default"}
                                            className={`text-xs ${!log.is_success ? "bg-red-500 text-white border-red-600" : ""}`}
                                        >
                                            {formatActionType(log.action_type)}
                                        </Badge>
                                        {log.category && (
                                            <Badge variant="default" className="text-xs capitalize">
                                                {log.category}
                                            </Badge>
                                        )}
                                        {log.confidence_score != null && (
                                            <div className="flex items-center gap-2">
                                                <span className="text-xs text-muted-foreground">Confidence:</span>
                                                <div className="flex items-center gap-1">
                                                    <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
                                                        <div
                                                            className={`h-full ${getConfidenceColor(log.confidence_score)}`}
                                                            style={{ width: `${log.confidence_score * 100}%` }}
                                                        />
                                                    </div>
                                                    <span className="text-xs font-medium">
                                                        {(log.confidence_score * 100).toFixed(0)}%
                                                    </span>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                    <p className="text-sm text-foreground">{log.explanation}</p>
                                    {log.error_message && (
                                        <div className="flex items-start gap-2 text-xs text-red-600 bg-red-100 px-2 py-1 rounded">
                                            <Icon name="AlertCircle" className="h-4 w-4 mt-0.5 flex-shrink-0" />
                                            <span>{log.error_message}</span>
                                        </div>
                                    )}
                                    <p className="text-xs text-muted-foreground">
                                        {formatDate(log.created_at)}
                                    </p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>

            {pageCount > 1 && (
                <div className="flex items-center justify-center gap-2 pt-4">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                        disabled={!hasPrev || loading}
                    >
                        <Icon name="ChevronLeft" className="h-4 w-4" />
                        Previous
                    </Button>
                    <span className="text-sm text-muted-foreground">
                        Page {page} of {pageCount}
                    </span>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setOffset(offset + PAGE_SIZE)}
                        disabled={!hasNext || loading}
                    >
                        Next
                        <Icon name="ChevronRight" className="h-4 w-4" />
                    </Button>
                </div>
            )}
        </div>
    );
}

