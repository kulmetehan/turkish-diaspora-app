import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { getAILogDetail, listAILogs, type AILogDetail, type AILogItem } from "@/lib/apiAdmin";

type Filters = {
    newsId: string;
    sourceKey: string;
    sourceName: string;
};

const PAGE_SIZE = 20;

export default function NewsAIDiagnosticsPanel() {
    const [viewMode, setViewMode] = useState<"news" | "location">("news");
    const [draftFilters, setDraftFilters] = useState<Filters>({ newsId: "", sourceKey: "", sourceName: "" });
    const [activeFilters, setActiveFilters] = useState<Filters>(draftFilters);
    const [logs, setLogs] = useState<AILogItem[]>([]);
    const [total, setTotal] = useState(0);
    const [offset, setOffset] = useState(0);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [detailOpen, setDetailOpen] = useState(false);
    const [detailLoading, setDetailLoading] = useState(false);
    const [detailData, setDetailData] = useState<AILogDetail | null>(null);
    const [pendingDetailId, setPendingDetailId] = useState<number | null>(null);

    useEffect(() => {
        let cancelled = false;
        async function load() {
            setLoading(true);
            setError(null);
            const params: Record<string, unknown> = {
                limit: PAGE_SIZE,
                offset,
            };
            if (viewMode === "news") {
                params.news_only = true;
                const trimmedId = activeFilters.newsId.trim();
                if (trimmedId) {
                    const parsed = Number(trimmedId);
                    if (!Number.isNaN(parsed)) {
                        params.news_id = parsed;
                    }
                }
                if (activeFilters.sourceKey.trim()) {
                    params.source_key = activeFilters.sourceKey.trim();
                }
                if (activeFilters.sourceName.trim()) {
                    params.source_name = activeFilters.sourceName.trim();
                }
            } else {
                params.news_only = false;
            }

            try {
                const resp = await listAILogs(params);
                if (cancelled) return;
                setLogs(resp.items);
                setTotal(resp.total);
            } catch (e: any) {
                if (cancelled) return;
                const message = e?.message || "Failed to load AI logs";
                setError(message);
                setLogs([]);
                setTotal(0);
                toast.error(message);
            } finally {
                if (!cancelled) {
                    setLoading(false);
                }
            }
        }
        load();
        return () => {
            cancelled = true;
        };
    }, [viewMode, activeFilters, offset]);

    useEffect(() => {
        if (!detailOpen || pendingDetailId == null) return;
        let cancelled = false;
        setDetailLoading(true);
        setDetailData(null);
        getAILogDetail(pendingDetailId)
            .then((detail) => {
                if (cancelled) return;
                setDetailData(detail);
            })
            .catch((e: any) => {
                if (cancelled) return;
                toast.error(e?.message || "Failed to load log detail");
            })
            .finally(() => {
                if (!cancelled) setDetailLoading(false);
            });
        return () => {
            cancelled = true;
        };
    }, [detailOpen, pendingDetailId]);

    const page = useMemo(() => Math.floor(offset / PAGE_SIZE) + 1, [offset]);
    const pageCount = useMemo(() => Math.max(1, Math.ceil(total / PAGE_SIZE)), [total]);

    const hasFiltersApplied =
        Boolean(activeFilters.newsId.trim()) ||
        Boolean(activeFilters.sourceKey.trim()) ||
        Boolean(activeFilters.sourceName.trim());

    function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setOffset(0);
        setActiveFilters(draftFilters);
    }

    function resetFilters() {
        const empty: Filters = { newsId: "", sourceKey: "", sourceName: "" };
        setDraftFilters(empty);
        setActiveFilters(empty);
        setOffset(0);
    }

    function handleSelect(logId: number) {
        setDetailOpen(true);
        setPendingDetailId(logId);
    }

    function closeDetail() {
        setDetailOpen(false);
        setPendingDetailId(null);
        setDetailData(null);
    }

    const canGoPrev = offset > 0;
    const canGoNext = offset + PAGE_SIZE < total;

    return (
        <div className="space-y-4">
            <Card>
                <CardHeader>
                    <CardTitle>AI Log Explorer</CardTitle>
                    <p className="text-sm text-muted-foreground">
                        Inspect AI prompts, responses, and outcomes for both news and location pipelines.
                    </p>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="flex flex-wrap items-center gap-3">
                        <span className="text-sm font-medium">View</span>
                        <div className="flex gap-2">
                            <Button
                                type="button"
                                variant={viewMode === "news" ? "default" : "outline"}
                                onClick={() => {
                                    setViewMode("news");
                                    setOffset(0);
                                }}
                                size="sm"
                            >
                                News logs
                            </Button>
                            <Button
                                type="button"
                                variant={viewMode === "location" ? "default" : "outline"}
                                onClick={() => {
                                    setViewMode("location");
                                    setOffset(0);
                                }}
                                size="sm"
                            >
                                Location logs
                            </Button>
                        </div>
                        {viewMode === "news" && (
                            <Badge variant="secondary" className="ml-auto">
                                {hasFiltersApplied ? "Filters active" : "News-only mode"}
                            </Badge>
                        )}
                    </div>

                    <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-4 md:grid-cols-3">
                        <div className="space-y-1">
                            <Label htmlFor="news-id">News ID</Label>
                            <Input
                                id="news-id"
                                value={draftFilters.newsId}
                                onChange={(e) => setDraftFilters((prev) => ({ ...prev, newsId: e.target.value }))}
                                placeholder="e.g. 1234"
                                disabled={viewMode !== "news"}
                            />
                        </div>
                        <div className="space-y-1">
                            <Label htmlFor="source-key">Source key</Label>
                            <Input
                                id="source-key"
                                value={draftFilters.sourceKey}
                                onChange={(e) => setDraftFilters((prev) => ({ ...prev, sourceKey: e.target.value }))}
                                placeholder="anp / rss42"
                                disabled={viewMode !== "news"}
                            />
                        </div>
                        <div className="space-y-1">
                            <Label htmlFor="source-name">Source name</Label>
                            <Input
                                id="source-name"
                                value={draftFilters.sourceName}
                                onChange={(e) => setDraftFilters((prev) => ({ ...prev, sourceName: e.target.value }))}
                                placeholder="ANP / Anadolu Ajansı"
                                disabled={viewMode !== "news"}
                            />
                        </div>
                        <div className="col-span-full flex flex-wrap gap-2">
                            <Button type="submit" disabled={viewMode !== "news"}>
                                Apply filters
                            </Button>
                            <Button type="button" variant="outline" onClick={resetFilters} disabled={viewMode !== "news"}>
                                Reset
                            </Button>
                        </div>
                    </form>
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle>Recent AI logs</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    {loading && (
                        <div className="text-sm text-muted-foreground">Loading logs…</div>
                    )}
                    {!loading && error && (
                        <div className="text-sm text-red-500">{error}</div>
                    )}
                    {!loading && !error && logs.length === 0 && (
                        <div className="text-sm text-muted-foreground">No AI logs found for the selected filters.</div>
                    )}
                    <div className="space-y-3">
                        {logs.map((log) => {
                            const isNews = Boolean(log.news_id);
                            return (
                                <Card key={log.id} className={cn("border", !log.is_success && "border-destructive/60")}>
                                    <CardContent className="p-4 space-y-3">
                                        <div className="flex flex-wrap items-center gap-2">
                                            <Badge variant={isNews ? "default" : "outline"}>
                                                {isNews ? "News" : "Location"}
                                            </Badge>
                                            <Badge variant={log.is_success ? "secondary" : "destructive"}>
                                                {log.is_success ? "Success" : "Error"}
                                            </Badge>
                                            <span className="text-sm font-medium">{log.action_type}</span>
                                            {log.model_used && (
                                                <span className="text-xs text-muted-foreground">{log.model_used}</span>
                                            )}
                                            <span className="text-xs text-muted-foreground ml-auto">
                                                {new Date(log.created_at).toLocaleString()}
                                            </span>
                                        </div>
                                        <div className="flex flex-wrap items-center gap-3 text-sm">
                                            {isNews ? (
                                                <>
                                                    <span className="text-muted-foreground">
                                                        Source: {log.news_source_name || log.news_source_key || "—"}
                                                    </span>
                                                    {log.news_id && (
                                                        <span className="text-muted-foreground">News ID: {log.news_id}</span>
                                                    )}
                                                </>
                                            ) : (
                                                <span className="text-muted-foreground">
                                                    Location ID: {log.location_id ?? "—"}
                                                </span>
                                            )}
                                            {log.category && (
                                                <Badge variant="outline" className="capitalize">
                                                    {log.category}
                                                </Badge>
                                            )}
                                        </div>
                                        <p className="text-sm text-muted-foreground">{log.explanation}</p>
                                        <div className="flex items-center justify-between">
                                            {log.confidence_score != null && (
                                                <div className="text-xs text-muted-foreground">
                                                    Confidence: {(log.confidence_score * 100).toFixed(1)}%
                                                </div>
                                            )}
                                            <Button
                                                type="button"
                                                variant="outline"
                                                size="sm"
                                                onClick={() => handleSelect(log.id)}
                                            >
                                                View details
                                            </Button>
                                        </div>
                                    </CardContent>
                                </Card>
                            );
                        })}
                    </div>
                    {logs.length > 0 && (
                        <div className="flex items-center justify-between pt-2">
                            <div className="text-sm text-muted-foreground">
                                Page {page} of {pageCount}
                            </div>
                            <div className="flex gap-2">
                                <Button type="button" variant="outline" size="sm" disabled={!canGoPrev} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
                                    Previous
                                </Button>
                                <Button type="button" variant="outline" size="sm" disabled={!canGoNext} onClick={() => setOffset(offset + PAGE_SIZE)}>
                                    Next
                                </Button>
                            </div>
                        </div>
                    )}
                </CardContent>
            </Card>

            <Dialog open={detailOpen} onOpenChange={(open) => (open ? setDetailOpen(true) : closeDetail())}>
                <DialogContent className="max-w-3xl">
                    <DialogHeader>
                        <DialogTitle>AI log details</DialogTitle>
                        <DialogDescription>
                            Inspect the exact prompt, raw response, and validated output returned by the model.
                        </DialogDescription>
                    </DialogHeader>
                    {detailLoading && <div className="text-sm text-muted-foreground">Loading log details…</div>}
                    {!detailLoading && !detailData && (
                        <div className="text-sm text-muted-foreground">Select a log to view details.</div>
                    )}
                    {!detailLoading && detailData && (
                        <div className="space-y-4">
                            <div className="grid gap-2 text-sm">
                                <div className="text-muted-foreground">Action: {detailData.action_type}</div>
                                <div className="text-muted-foreground">
                                    Result: {detailData.is_success ? "Success" : detailData.error_message || "Error"}
                                </div>
                                {detailData.news_title && (
                                    <div className="text-muted-foreground">
                                        Title: {detailData.news_title}
                                    </div>
                                )}
                                <div className="text-muted-foreground">
                                    Timestamp: {new Date(detailData.created_at).toLocaleString()}
                                </div>
                                <div className="text-muted-foreground">
                                    Context:{" "}
                                    {detailData.news_id
                                        ? `News ${detailData.news_id} (${detailData.news_source_name || detailData.news_source_key || "unknown"})`
                                        : `Location ${detailData.location_id ?? "—"}`}
                                </div>
                            </div>
                            <JsonBlock title="Prompt" value={detailData.prompt} />
                            <JsonBlock title="Raw response" value={detailData.raw_response} />
                            <JsonBlock title="Validated output" value={detailData.validated_output} />
                        </div>
                    )}
                </DialogContent>
            </Dialog>
        </div>
    );
}

function JsonBlock({ title, value }: { title: string; value?: unknown }) {
    return (
        <div className="space-y-2">
            <div className="text-sm font-medium">{title}</div>
            {value ? (
                <pre className="max-h-64 overflow-auto rounded-md bg-muted p-3 text-xs">
                    {typeof value === "string" ? value : JSON.stringify(value, null, 2)}
                </pre>
            ) : (
                <div className="text-xs text-muted-foreground">No data</div>
            )}
        </div>
    );
}

