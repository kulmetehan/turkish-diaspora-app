import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { type WorkerStatus } from "@/lib/api";

const WORKER_STATUS_BADGE_CLASSES: Record<WorkerStatus["status"], string> = {
    ok: "bg-emerald-100 text-emerald-800 border-emerald-200",
    warning: "bg-amber-100 text-amber-800 border-amber-200",
    error: "bg-red-100 text-red-800 border-red-200",
    unknown: "bg-slate-100 text-slate-700 border-slate-200",
};

// Map worker IDs from metrics snapshot to backend bot values for run endpoint
const BOT_ID_TO_RUN_VALUE: Record<string, string> = {
    discovery_bot: "discovery",
    verify_locations_bot: "verify",
    monitor_bot: "monitor",
    classify_bot: "classify",
};

// Bots that can be manually triggered
const SUPPORTED_BOTS = new Set(["discovery_bot", "verify_locations_bot", "monitor_bot", "classify_bot"]);

function formatLastRun(value: string | null | undefined): string {
    if (!value) return "Not yet run";
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

function formatCountWithContext(value: number | null | undefined, windowLabel?: string | null): string {
    if (value === null || value === undefined) return "–";
    const label = windowLabel && windowLabel.trim().length > 0 ? windowLabel : "recent window";
    return `${value} (${label})`;
}

function formatQuotaInfo(quota: Record<string, number | null> | null | undefined): string {
    if (!quota || Object.keys(quota).length === 0) {
        return "–";
    }
    return Object.entries(quota)
        .map(([key, val]) => `${key}: ${val ?? "n/a"}`)
        .join(", ");
}

interface WorkerCardProps {
    worker: WorkerStatus;
    onRunClick?: (botId: string) => void;
}

export default function WorkerCard({ worker, onRunClick }: WorkerCardProps) {
    const canRun = SUPPORTED_BOTS.has(worker.id);
    const runBotValue = BOT_ID_TO_RUN_VALUE[worker.id];

    const handleRunClick = () => {
        if (canRun && onRunClick && runBotValue) {
            onRunClick(runBotValue);
        }
    };

    const notePreview = worker.notes && worker.notes.trim().length > 0
        ? worker.notes.split("\n")[0]
        : "–";

    return (
        <Card className="rounded-2xl shadow-sm">
            <CardHeader>
                <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">{worker.label}</CardTitle>
                    <Badge
                        variant="outline"
                        className={`text-xs font-medium px-2 py-1 ${WORKER_STATUS_BADGE_CLASSES[worker.status]}`}
                    >
                        {worker.status.toUpperCase()}
                    </Badge>
                </div>
                <div className="text-xs text-muted-foreground mt-1">{worker.id}</div>
            </CardHeader>
            <CardContent className="space-y-2">
                <div className="text-sm">
                    <div className="font-medium text-muted-foreground">Last run</div>
                    <div>{formatLastRun(worker.lastRun)}</div>
                </div>
                {worker.durationSeconds !== null && worker.durationSeconds !== undefined && (
                    <div className="text-sm">
                        <div className="font-medium text-muted-foreground">Duration</div>
                        <div>{formatDurationSeconds(worker.durationSeconds)}</div>
                    </div>
                )}
                <div className="text-sm">
                    <div className="font-medium text-muted-foreground">Processed</div>
                    <div>{formatCountWithContext(worker.processedCount, worker.windowLabel)}</div>
                </div>
                {worker.errorCount !== null && worker.errorCount !== undefined && worker.errorCount > 0 && (
                    <div className="text-sm">
                        <div className="font-medium text-muted-foreground">Errors</div>
                        <div className="text-red-600">{formatCountWithContext(worker.errorCount, worker.windowLabel)}</div>
                    </div>
                )}
                {worker.quotaInfo && Object.keys(worker.quotaInfo).length > 0 && (
                    <div className="text-sm">
                        <div className="font-medium text-muted-foreground">Quota</div>
                        <div className="text-xs">{formatQuotaInfo(worker.quotaInfo)}</div>
                    </div>
                )}
                {notePreview !== "–" && (
                    <div className="text-sm">
                        <div className="font-medium text-muted-foreground">Notes</div>
                        <div className="text-xs whitespace-pre-line">{notePreview}</div>
                    </div>
                )}
            </CardContent>
            {canRun && onRunClick && (
                <CardFooter>
                    <Button onClick={handleRunClick} className="w-full" variant="outline">
                        Run worker
                    </Button>
                </CardFooter>
            )}
        </Card>
    );
}

