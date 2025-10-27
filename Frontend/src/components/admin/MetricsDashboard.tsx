/**
 * MetricsDashboard (Admin > Metrics tab)
 *
 * Dev setup:
 *   cd Frontend
 *   npm install
 *   npm run dev
 *
 * "recharts" MUST be present under dependencies in Frontend/package.json
 * and installed in Frontend/node_modules.
 *
 * This component is lazy-loaded by AdminHomePage.tsx so that
 * a missing recharts dependency cannot crash the entire app at startup.
 *
 * DO NOT touch routing, auth, or other admin tabs from here.
 */
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getMetricsSnapshot, type MetricsSnapshot } from "@/lib/api";
import { Activity, AlertTriangle, Gauge, LineChart as LineChartIcon, MapPin, TrendingUp } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
    CartesianGrid,
    Line,
    LineChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts";

const RECHARTS_OK =
    typeof ResponsiveContainer !== "undefined" &&
    typeof LineChart !== "undefined" &&
    typeof Line !== "undefined";

function formatPercentFromFraction(val: number | undefined | null): string {
    if (val === undefined || val === null) return "n/a";
    return `${(val * 100).toFixed(2)}%`;
}

function formatPercentRaw(val: number | undefined | null): string {
    if (val === undefined || val === null) return "n/a";
    return `${val.toFixed(2)}%`;
}

function formatLatency(ms: number | undefined | null): string {
    if (!ms || ms === 0) return "n/a";
    return `${ms} ms`;
}

export default function MetricsDashboard() {
    const [data, setData] = useState<MetricsSnapshot | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let isMounted = true;
        (async () => {
            try {
                const res = await getMetricsSnapshot();
                if (isMounted) setData(res);
            } catch (e: any) {
                if (isMounted) setError(e?.message || "Failed to load metrics");
            } finally {
                if (isMounted) setLoading(false);
            }
        })();
        return () => { isMounted = false; };
    }, []);

    const chartData = useMemo(() => {
        const arr = data?.weekly_candidates || [];
        const mapped = arr.map((d) => ({
            week_start: typeof d.week_start === "string" ? d.week_start : (d.week_start as any),
            count: d.count,
        }));
        return mapped.sort((a, b) => a.week_start.localeCompare(b.week_start));
    }, [data]);

    if (error) {
        return (
            <Card className="rounded-2xl shadow-sm">
                <CardHeader>
                    <CardTitle>Metrics</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="p-2 text-sm text-destructive">{error}</div>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="space-y-4">
            {/* KPI Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {/* Verified locations (Rotterdam) */}
                <Card className="rounded-2xl shadow-sm">
                    <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                        <CardTitle className="text-sm font-medium">Verified (Rotterdam)</CardTitle>
                        <MapPin className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        {loading ? (
                            <Skeleton className="h-8 w-16" />
                        ) : (
                            <div className="text-2xl font-semibold">
                                {data?.city_progress.rotterdam.verified_count ?? 0}
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Coverage ratio */}
                <Card className="rounded-2xl shadow-sm">
                    <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                        <CardTitle className="text-sm font-medium">Coverage ratio</CardTitle>
                        <Gauge className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        {loading ? (
                            <Skeleton className="h-8 w-16" />
                        ) : (
                            <div className="text-2xl font-semibold">
                                {formatPercentFromFraction(data?.city_progress.rotterdam.coverage_ratio)}
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Weekly growth */}
                <Card className="rounded-2xl shadow-sm">
                    <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                        <CardTitle className="text-sm font-medium">Weekly growth</CardTitle>
                        <TrendingUp className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        {loading ? (
                            <Skeleton className="h-8 w-16" />
                        ) : (
                            <div className="text-2xl font-semibold">
                                {formatPercentRaw(data?.city_progress.rotterdam.growth_weekly)}
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Task error rate */}
                <Card className="rounded-2xl shadow-sm">
                    <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                        <CardTitle className="text-sm font-medium">Task error rate (60m)</CardTitle>
                        <AlertTriangle className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        {loading ? (
                            <Skeleton className="h-8 w-16" />
                        ) : (
                            <div className="text-2xl font-semibold">
                                {formatPercentFromFraction(data?.quality.task_error_rate_60m)}
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Google 429 bursts */}
                <Card className="rounded-2xl shadow-sm">
                    <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                        <CardTitle className="text-sm font-medium">Google 429 (60m)</CardTitle>
                        <LineChartIcon className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        {loading ? (
                            <Skeleton className="h-8 w-8" />
                        ) : (
                            <div className="text-2xl font-semibold">
                                {data?.quality.google429_last60m ?? 0}
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Latency (p50/avg/max) */}
                <Card className="rounded-2xl shadow-sm">
                    <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                        <CardTitle className="text-sm font-medium">Latency (p50/avg/max)</CardTitle>
                        <Activity className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        {loading ? (
                            <Skeleton className="h-8 w-24" />
                        ) : (
                            <div className="text-sm font-medium">
                                {formatLatency(data?.latency.p50_ms)} / {formatLatency(data?.latency.avg_ms)} / {formatLatency(data?.latency.max_ms)}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* Time series chart */}
            <Card className="rounded-2xl shadow-sm">
                <CardHeader>
                    <CardTitle>New candidates/week</CardTitle>
                </CardHeader>
                <CardContent>
                    {loading ? (
                        <div className="space-y-2">
                            <Skeleton className="h-6 w-32" />
                            <Skeleton className="h-48 w-full" />
                        </div>
                    ) : chartData.length === 0 ? (
                        <div className="text-sm text-muted-foreground">No historical candidate data yet</div>
                    ) : !RECHARTS_OK ? (
                        <div className="text-sm text-destructive">
                            Charts unavailable (Recharts not loaded). Did you run npm install in /Frontend?
                        </div>
                    ) : (
                        <div className="h-64">
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={chartData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis dataKey="week_start" tick={{ fontSize: 12 }} />
                                    <YAxis tick={{ fontSize: 12 }} />
                                    <Tooltip />
                                    <Line type="monotone" dataKey="count" strokeWidth={2} dot={false} name="New candidates/week" />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}


