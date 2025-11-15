import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { type WorkerStatus } from "@/lib/api";

export const DIAGNOSIS_INFO: Record<string, {
    title: string;
    explanation: string;
    metrics?: string[];
    suggestions: string[];
}> = {
    OK: {
        title: "Worker Operating Normally",
        explanation: "This worker is functioning as expected with no issues detected.",
        suggestions: [],
    },
    NEVER_RAN: {
        title: "Worker Has Not Run Yet",
        explanation: "This worker has not executed since deployment. This may be normal if the worker is scheduled to run periodically or has not been triggered yet.",
        suggestions: [
            "Check if the worker is scheduled to run automatically",
            "Manually trigger the worker from the Worker controls section",
            "Verify that the worker service is properly configured and deployed",
        ],
    },
    OSM_ERROR_RATE_HIGH: {
        title: "High OSM API Error Rate",
        explanation: "The DiscoveryBot is experiencing a high rate of errors when calling the OpenStreetMap Overpass API. This may indicate rate limiting, network issues, or API service problems.",
        metrics: ["overpass_error_count_last_60m", "overpass_429_last_60m"],
        suggestions: [
            "Increase inter-call sleep time in discovery runs to reduce rate limiting",
            "Check Overpass API status and availability",
            "Reduce max cells per run to lower API call frequency",
            "Review network connectivity and firewall rules",
        ],
    },
    NO_NEW_INSERTS_LAST_30_DAYS: {
        title: "No New Locations Inserted in 30 Days",
        explanation: "DiscoveryBot has been running but has not inserted any new locations in the past 30 days. This may indicate that all discoverable locations have already been found, or there may be an issue with the discovery process.",
        metrics: ["total_inserted_30d", "total_runs_30d"],
        suggestions: [
            "Review discovery run logs to check for errors or warnings",
            "Verify that discovery is running in areas with Turkish businesses",
            "Check if discovery categories are correctly configured",
            "Consider expanding the search area or adjusting discovery parameters",
        ],
    },
    AI_ERROR_RATE_HIGH: {
        title: "High AI Service Error Rate",
        explanation: "The worker is experiencing a high rate of errors when calling AI services (OpenAI). This may indicate API rate limiting, authentication issues, or service unavailability.",
        metrics: ["error_count", "processed_count"],
        suggestions: [
            "Check OpenAI API key validity and rate limits",
            "Review AI service logs for specific error messages",
            "Reduce the number of concurrent AI requests",
            "Verify network connectivity to OpenAI services",
            "Consider temporarily pausing the worker if errors persist",
        ],
    },
    TASK_QUEUE_BACKLOG: {
        title: "Verification Task Queue Backlog",
        explanation: "The verification task queue has a significant backlog with many pending tasks compared to processing tasks. This indicates that tasks are being created faster than they can be processed.",
        metrics: ["pending_queue", "processing_queue"],
        suggestions: [
            "Increase the number of verification workers or processing capacity",
            "Review and optimize verification task processing time",
            "Check if verification workers are running and healthy",
            "Consider reducing the rate of task creation if appropriate",
            "Monitor worker logs for processing errors or bottlenecks",
        ],
    },
    METRICS_DATA_MISSING: {
        title: "Metrics Data Unavailable",
        explanation: "The required database tables for worker metrics are missing. This typically means database migrations have not been run or the tables were not created properly.",
        suggestions: [
            "Run database migrations to create the required metrics tables",
            "Verify database connection and schema",
            "Check migration logs for any errors",
            "Contact the development team if migrations are up to date",
        ],
    },
    UNKNOWN: {
        title: "Unknown Worker Status",
        explanation: "The worker status could not be determined. This may indicate a temporary issue with metrics collection or an unexpected error.",
        suggestions: [
            "Check worker logs for recent errors or warnings",
            "Verify that the worker service is running",
            "Refresh the metrics dashboard to see if the issue resolves",
            "Contact the development team if the issue persists",
        ],
    },
};

export interface WorkerDiagnosisDialogProps {
    worker: WorkerStatus | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

export default function WorkerDiagnosisDialog({ worker, open, onOpenChange }: WorkerDiagnosisDialogProps) {
    // Don't render dialog content if no worker is selected
    if (!worker) {
        return null;
    }

    const diagnosisCode = worker.diagnosisCode || "UNKNOWN";
    const info = DIAGNOSIS_INFO[diagnosisCode] || {
        title: "Diagnosis Unavailable",
        explanation: `No diagnosis information available for code: ${diagnosisCode}`,
        suggestions: [],
    };

    // Get relevant metrics
    const relevantMetrics: Array<{ label: string; value: string | number | null }> = [];
    if (info.metrics) {
        for (const metricKey of info.metrics) {
            if (metricKey === "error_count") {
                relevantMetrics.push({ label: "Error Count", value: worker.errorCount });
            } else if (metricKey === "processed_count") {
                relevantMetrics.push({ label: "Processed Count", value: worker.processedCount });
            } else if (worker.quotaInfo && metricKey in worker.quotaInfo) {
                relevantMetrics.push({ label: metricKey.replace(/_/g, " "), value: worker.quotaInfo[metricKey] });
            }
        }
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>{worker.label} - {info.title}</DialogTitle>
                    <DialogDescription>
                        Diagnosis Code: <code className="text-xs bg-muted px-1 py-0.5 rounded">{diagnosisCode}</code>
                    </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                    <div>
                        <h4 className="font-semibold text-sm mb-2">Explanation</h4>
                        <p className="text-sm text-muted-foreground">{info.explanation}</p>
                    </div>

                    {relevantMetrics.length > 0 && (
                        <div>
                            <h4 className="font-semibold text-sm mb-2">Key Metrics</h4>
                            <div className="space-y-1">
                                {relevantMetrics.map((metric, idx) => (
                                    <div key={idx} className="text-sm">
                                        <span className="font-medium">{metric.label}:</span>{" "}
                                        <span className="text-muted-foreground">
                                            {metric.value !== null && metric.value !== undefined ? metric.value : "n/a"}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {worker.quotaInfo && Object.keys(worker.quotaInfo).length > 0 && (
                        <div>
                            <h4 className="font-semibold text-sm mb-2">All Metrics</h4>
                            <div className="text-sm text-muted-foreground space-y-1">
                                {Object.entries(worker.quotaInfo).map(([key, value]) => (
                                    <div key={key}>
                                        <span className="font-medium">{key.replace(/_/g, " ")}:</span>{" "}
                                        {value !== null && value !== undefined ? value : "n/a"}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {info.suggestions.length > 0 && (
                        <div>
                            <h4 className="font-semibold text-sm mb-2">Suggested Actions</h4>
                            <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                                {info.suggestions.map((suggestion, idx) => (
                                    <li key={idx}>{suggestion}</li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {worker.notes && (
                        <div>
                            <h4 className="font-semibold text-sm mb-2">Additional Notes</h4>
                            <p className="text-sm text-muted-foreground whitespace-pre-line">{worker.notes}</p>
                        </div>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    );
}

