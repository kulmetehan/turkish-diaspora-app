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
import { fetchCategories, type CategoryOption } from "@/api/fetchLocations";
import WorkerDiagnosisDialog from "@/components/admin/WorkerDiagnosisDialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { getCategoryHealthMetrics, getCitiesOverview, getDiscoveryKPIs, getMetricsSnapshot, type CategoryHealth, type CategoryHealthResponse, type CitiesOverview, type DiscoveryKPIs, type MetricsSnapshot, type WorkerRun, type WorkerStatus } from "@/lib/api";
import { getLocationStateMetrics, runWorker, type LocationStateMetrics } from "@/lib/apiAdmin";
import { cn } from "@/lib/ui/cn";
import { Activity, AlertTriangle, ArrowUpDown, Database, Gauge, Info, LineChart as LineChartIcon, MapPin, TrendingUp } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
    CartesianGrid,
    Line,
    LineChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts";
import { toast } from "sonner";

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

const WORKER_STATUS_BADGE_CLASSES: Record<WorkerStatus["status"], string> = {
    ok: "bg-emerald-100 text-emerald-800 border-emerald-200",
    warning: "bg-amber-100 text-amber-800 border-amber-200",
    error: "bg-red-100 text-red-800 border-red-200",
    unknown: "bg-slate-100 text-slate-700 border-slate-200",
};


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

// Helper function to determine category health status
// Always uses backend-computed status (single source of truth)
function getCategoryHealthStatus(category: CategoryHealth): 'healthy' | 'warning' | 'degraded' | 'critical' | 'no_data' {
    // Always use backend-computed status
    return category.status || 'no_data';
}

// Category Health Table Component
function CategoryHealthTable({ categoryHealth, categoryOptions }: { categoryHealth: CategoryHealthResponse; categoryOptions: CategoryOption[] }) {
    const [sortField, setSortField] = useState<'category' | 'zeroResultRatio' | 'turkishCoverage' | 'aiPrecision' | 'inserted' | 'promoted'>('category');
    const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

    const categoryMap = useMemo(() => {
        const map = new Map<string, string>();
        categoryOptions.forEach(opt => {
            map.set(opt.key, opt.label);
        });
        return map;
    }, [categoryOptions]);

    const sortedCategories = useMemo(() => {
        const entries = Object.entries(categoryHealth.categories);
        return entries.sort(([keyA, catA], [keyB, catB]) => {
            let aVal: number | string;
            let bVal: number | string;

            switch (sortField) {
                case 'category':
                    aVal = categoryMap.get(keyA) || keyA;
                    bVal = categoryMap.get(keyB) || keyB;
                    break;
                case 'zeroResultRatio':
                    aVal = catA.overpassZeroResultRatioPct;
                    bVal = catB.overpassZeroResultRatioPct;
                    break;
                case 'turkishCoverage':
                    aVal = catA.turkishCoverageRatioPct;
                    bVal = catB.turkishCoverageRatioPct;
                    break;
                case 'aiPrecision':
                    aVal = catA.aiPrecisionPct;
                    bVal = catB.aiPrecisionPct;
                    break;
                case 'inserted':
                    aVal = catA.insertedLocationsLast7d;
                    bVal = catB.insertedLocationsLast7d;
                    break;
                case 'promoted':
                    aVal = catA.promotedVerifiedLast7d;
                    bVal = catB.promotedVerifiedLast7d;
                    break;
                default:
                    return 0;
            }

            if (typeof aVal === 'string' && typeof bVal === 'string') {
                return sortDirection === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
            } else {
                return sortDirection === 'asc' ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number);
            }
        });
    }, [categoryHealth.categories, sortField, sortDirection, categoryMap]);

    const handleSort = (field: typeof sortField) => {
        if (sortField === field) {
            setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
        } else {
            setSortField(field);
            setSortDirection('asc');
        }
    };

    const SortButton = ({ field, children }: { field: typeof sortField; children: React.ReactNode }) => (
        <button
            onClick={() => handleSort(field)}
            className="flex items-center gap-1 hover:text-foreground transition-colors"
        >
            {children}
            <ArrowUpDown className="h-3 w-3" />
        </button>
    );

    return (
        <div className="space-y-4">
            <div className="text-sm text-muted-foreground">
                Time windows: Overpass {categoryHealth.timeWindows.overpassWindowHours}h,
                Inserts/Classifications/Promotions {categoryHealth.timeWindows.insertsWindowDays}d
                <span className="ml-2 text-xs">
                    (Turkish coverage compares {categoryHealth.timeWindows.insertsWindowDays}d inserts 
                    to {categoryHealth.timeWindows.overpassWindowHours}h Overpass finds)
                </span>
            </div>
            <div className="overflow-x-auto">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="border-b">
                            <th className="text-left p-2">
                                <SortButton field="category">Category</SortButton>
                            </th>
                            <th className="text-right p-2">
                                <SortButton field="turkishCoverage">Turkish Coverage %</SortButton>
                            </th>
                            <th className="text-right p-2">Overpass Calls ({categoryHealth.timeWindows.overpassWindowHours}h)</th>
                            <th className="text-right p-2">
                                <SortButton field="inserted">Inserted (7d)</SortButton>
                            </th>
                            <th className="text-right p-2">AI Classifications (7d)</th>
                            <th className="text-right p-2">
                                <SortButton field="aiPrecision">AI Precision %</SortButton>
                            </th>
                            <th className="text-right p-2">Keep / Ignore</th>
                            <th className="text-right p-2">
                                <SortButton field="promoted">Verified (7d)</SortButton>
                            </th>
                            <th className="text-center p-2">Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {sortedCategories.map(([key, cat]) => {
                            const status = getCategoryHealthStatus(cat);
                            const categoryLabel = categoryMap.get(key) || key;
                            const statusBadgeClass =
                                status === 'healthy' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' :
                                    status === 'warning' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' :
                                        status === 'degraded' ? 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200' :
                                            status === 'critical' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' :
                                                'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300';

                            return (
                                <tr key={key} className="border-b hover:bg-muted/50">
                                    <td className="p-2 font-medium">{categoryLabel}</td>
                                    <td className="text-right p-2">
                                        {cat.overpassFound > 0 ? `${cat.turkishCoverageRatioPct.toFixed(1)}%` : '-'}
                                    </td>
                                    <td className="text-right p-2">{cat.overpassCalls}</td>
                                    <td className="text-right p-2">{cat.insertedLocationsLast7d}</td>
                                    <td className="text-right p-2">{cat.aiClassificationsLast7d}</td>
                                    <td className="text-right p-2">
                                        {cat.aiClassificationsLast7d > 0 ? `${cat.aiPrecisionPct.toFixed(1)}%` : '-'}
                                    </td>
                                    <td className="text-right p-2">
                                        {cat.aiActionKeep > 0 || cat.aiActionIgnore > 0
                                            ? `${cat.aiActionKeep} / ${cat.aiActionIgnore}`
                                            : '-'
                                        }
                                    </td>
                                    <td className="text-right p-2">{cat.promotedVerifiedLast7d}</td>
                                    <td className="text-center p-2">
                                        <Badge className={statusBadgeClass}>
                                            {status === 'healthy' ? 'Healthy' :
                                                status === 'warning' ? 'Warning' :
                                                    status === 'degraded' ? 'Degraded' :
                                                        status === 'critical' ? 'Critical' :
                                                            'No Data'}
                                        </Badge>
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

export default function MetricsDashboard() {
    const [data, setData] = useState<MetricsSnapshot | null>(null);
    const [discoveryKPIs, setDiscoveryKPIs] = useState<DiscoveryKPIs | null>(null);
    const [categoryHealth, setCategoryHealth] = useState<CategoryHealthResponse | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [loadingKPIs, setLoadingKPIs] = useState<boolean>(true);
    const [loadingCategoryHealth, setLoadingCategoryHealth] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);
    const [pollIntervalMs, setPollIntervalMs] = useState<number>(60000);
    const [categoryOptions, setCategoryOptions] = useState<CategoryOption[]>([]);
    const [categoriesLoading, setCategoriesLoading] = useState<boolean>(true);
    const [selectedBot, setSelectedBot] = useState<string | undefined>("discovery");
    const [selectedCity, setSelectedCity] = useState<string | undefined>(undefined);
    const [selectedCategory, setSelectedCategory] = useState<string | undefined>(undefined);
    const [isRunningWorker, setIsRunningWorker] = useState<boolean>(false);
    const [selectedWorker, setSelectedWorker] = useState<WorkerStatus | null>(null);
    const [selectedRun, setSelectedRun] = useState<WorkerRun | null>(null);
    const isMountedRef = useRef(false);
    const pollIntervalRef = useRef<number | null>(null);
    const pollIntervalMsRef = useRef<number>(60000);

    const ALL_BOTS = "ALL_BOTS";
    const ALL_CITIES = "ALL_CITIES";
    const ALL_CATEGORIES = "ALL_CATEGORIES";

    const botOptions = useMemo(
        () => [
            { value: "discovery", label: "Discovery" },
            { value: "classify", label: "Classify" },
            { value: "verify", label: "Verify" },
            { value: "monitor", label: "Monitor" },
        ],
        []
    );
    const [citiesOverview, setCitiesOverview] = useState<CitiesOverview | null>(null);
    const [locationStateMetrics, setLocationStateMetrics] = useState<LocationStateMetrics | null>(null);
    const cityOptions = useMemo(() => {
        if (citiesOverview?.cities && citiesOverview.cities.length > 0) {
            return citiesOverview.cities
                .filter(city => city.has_districts) // Only show cities with districts configured
                .map(city => ({
                    value: city.city_key,
                    label: city.city_name,
                }));
        }
        // Fallback to Rotterdam if cities not loaded yet
        return [{ value: "rotterdam", label: "Rotterdam" }];
    }, [citiesOverview]);
    const categoryDisabled = selectedBot === "monitor";

    useEffect(() => {
        if (categoryDisabled) {
            setSelectedCategory(undefined);
        }
    }, [categoryDisabled]);

    const loadCategoryHealth = useCallback(async () => {
        try {
            setLoadingCategoryHealth(true);
            const healthData = await getCategoryHealthMetrics();
            setCategoryHealth(healthData);
        } catch (e: any) {
            console.error("Failed to load category health metrics:", e);
            // Don't set error state for category health, just log it
        } finally {
            setLoadingCategoryHealth(false);
        }
    }, []);

    const loadLocationStateMetrics = useCallback(async () => {
        try {
            const metrics = await getLocationStateMetrics();
            setLocationStateMetrics(metrics);
        } catch (e: any) {
            console.error("Failed to load location state metrics:", e);
            // Don't set error state, just log it
        }
    }, []);

    const loadMetrics = useCallback(async () => {
        try {
            const res = await getMetricsSnapshot();
            if (!isMountedRef.current) return;
            setData(res);
            setError(null);
            const hasActive = Array.isArray(res.currentRuns) && res.currentRuns.some((run) =>
                ["pending", "running"].includes(run.status)
            );
            const desiredInterval = hasActive ? 5000 : 60000;

            // Update state for UI display
            setPollIntervalMs((prev) => {
                if (prev !== desiredInterval) {
                    return desiredInterval;
                }
                return prev;
            });

            // Update ref and recreate interval if needed
            if (pollIntervalMsRef.current !== desiredInterval) {
                pollIntervalMsRef.current = desiredInterval;

                // Clear existing interval
                if (pollIntervalRef.current !== null) {
                    window.clearInterval(pollIntervalRef.current);
                }

                // Create new interval with updated timing
                pollIntervalRef.current = window.setInterval(() => {
                    loadMetrics();
                }, desiredInterval);
            }
        } catch (e: any) {
            if (!isMountedRef.current) return;
            setError(e?.message || "Failed to load metrics");
        } finally {
            if (!isMountedRef.current) return;
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadMetrics();

        // Initialize ref with current poll interval
        pollIntervalMsRef.current = pollIntervalMs;

        // Set up initial interval
        pollIntervalRef.current = window.setInterval(() => {
            loadMetrics();
        }, pollIntervalMs);

        return () => {
            if (pollIntervalRef.current !== null) {
                window.clearInterval(pollIntervalRef.current);
                pollIntervalRef.current = null;
            }
        };
    }, [loadMetrics]); // Only depend on loadMetrics, not pollIntervalMs

    useEffect(() => {
        isMountedRef.current = true;
        return () => {
            isMountedRef.current = false;
        };
    }, []);

    // Load categories from dynamic registry
    useEffect(() => {
        let cancelled = false;
        setCategoriesLoading(true);
        fetchCategories()
            .then((cats) => {
                if (!cancelled) {
                    setCategoryOptions(cats);
                }
            })
            .catch((e) => {
                if (!cancelled) {
                    console.warn("Failed to load categories:", e);
                    setCategoryOptions([]);
                }
            })
            .finally(() => {
                if (!cancelled) {
                    setCategoriesLoading(false);
                }
            });
        return () => {
            cancelled = true;
        };
    }, []);

    useEffect(() => {
        let isMounted = true;
        (async () => {
            try {
                const res = await getDiscoveryKPIs(30);
                if (isMounted) setDiscoveryKPIs(res);
            } catch (e: any) {
                // Silently fail for KPIs - they're optional
                console.warn("Failed to load discovery KPIs:", e);
            } finally {
                if (isMounted) setLoadingKPIs(false);
            }
        })();
        return () => { isMounted = false; };
    }, []);

    // Load category health metrics on mount
    useEffect(() => {
        let cancelled = false;
        loadCategoryHealth().catch((e) => {
            if (!cancelled) {
                console.error("Failed to load category health:", e);
            }
        });
        return () => { cancelled = true; };
    }, [loadCategoryHealth]);

    // Load location state metrics on mount
    useEffect(() => {
        let cancelled = false;
        loadLocationStateMetrics().catch((e) => {
            if (!cancelled) {
                console.error("Failed to load location state metrics:", e);
            }
        });
        return () => { cancelled = true; };
    }, [loadLocationStateMetrics]);

    // Load cities overview for city selector
    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const overview = await getCitiesOverview();
                if (!cancelled) {
                    setCitiesOverview(overview);
                    // Auto-select first city with districts if none selected
                    if (!selectedCity && overview.cities.length > 0) {
                        const firstCityWithDistricts = overview.cities.find(c => c.has_districts);
                        if (firstCityWithDistricts) {
                            setSelectedCity(firstCityWithDistricts.city_key);
                        }
                    }
                }
            } catch (e: any) {
                console.warn("Failed to load cities overview:", e);
            }
        })();
        return () => { cancelled = true; };
    }, [selectedCity]);

    const chartData = useMemo(() => {
        const arr = data?.weeklyCandidates || [];
        const mapped = arr.map((d) => ({
            week_start: typeof d.weekStart === "string" ? d.weekStart : (d.weekStart as any),
            count: d.count,
        }));
        return mapped.sort((a, b) => a.week_start.localeCompare(b.week_start));
    }, [data]);
    const categorySelectOptions = useMemo(() => {
        // Filter out empty/invalid categories and return unique options
        return categoryOptions.filter((cat) => cat && cat.key && cat.key.trim().length > 0);
    }, [categoryOptions]);
    const activeRuns: WorkerRun[] = data?.currentRuns ?? [];
    const workerStatuses = data?.workers ?? [];
    const hasActiveRuns = activeRuns.length > 0;

    // Get city progress for selected city (fallback to rotterdam for backward compatibility)
    const selectedCityKey = selectedCity || "rotterdam";
    const cityProgress = data?.cityProgress?.cities?.[selectedCityKey]
        ?? data?.cityProgress?.rotterdam
        ?? null;
    const qualityMetrics = data?.quality ?? null;
    const discoverySummary = data?.discovery ?? null;
    const latencyMetrics = data?.latency ?? null;
    const verifiedCount = cityProgress?.verifiedCount ?? 0;
    const coverageRatio = cityProgress?.coverageRatio ?? 0;
    const growthWeekly = cityProgress?.growthWeekly ?? 0;
    const conversionRate14d = qualityMetrics?.conversionRateVerified14d ?? 0;
    const taskErrorRate = qualityMetrics?.taskErrorRate60m ?? 0;
    const google429Last60m = qualityMetrics?.google429Last60m ?? 0;
    const newCandidatesWeekly = discoverySummary?.newCandidatesPerWeek ?? 0;
    const latencyP50 = latencyMetrics?.p50Ms ?? 0;
    const latencyAvg = latencyMetrics?.avgMs ?? 0;
    const latencyMax = latencyMetrics?.maxMs ?? 0;

    const handleRunWorker = useCallback(async () => {
        const bot = selectedBot ?? botOptions[0]?.value ?? "discovery";
        const payload: { bot: string; city?: string; category?: string } = { bot };
        if (selectedCity) {
            payload.city = selectedCity;
        }
        if (selectedCategory && !categoryDisabled) {
            payload.category = selectedCategory;
        }
        setIsRunningWorker(true);
        try {
            const result = await runWorker(payload) as {
                run_id?: string | null;
                tracking_available?: boolean;
                detail?: string;
            };
            if (result?.tracking_available === false) {
                toast.warning(
                    result?.detail || "Worker run accepted, but progress tracking is not available yet."
                );
            } else {
                toast.success("Worker run created.");
                setPollIntervalMs((prev) => (prev === 5000 ? prev : 5000));
            }
            await loadMetrics();
        } catch (e: any) {
            toast.error(e?.message || "Failed to trigger worker run.");
        } finally {
            setIsRunningWorker(false);
        }
    }, [categoryDisabled, loadMetrics, selectedBot, selectedCategory, selectedCity]);

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
            {/* City Selector */}
            <Card className="rounded-2xl shadow-sm">
                <CardHeader>
                    <CardTitle>City Selection</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="space-y-2">
                        <Label htmlFor="metrics-city-selector">Select City</Label>
                        <Select
                            value={selectedCity ?? ALL_CITIES}
                            onValueChange={(next) =>
                                setSelectedCity(next === ALL_CITIES ? undefined : next)
                            }
                        >
                            <SelectTrigger id="metrics-city-selector">
                                <SelectValue placeholder="Select a city" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value={ALL_CITIES}>All cities</SelectItem>
                                {cityOptions.map((option) => (
                                    <SelectItem key={option.value} value={option.value}>
                                        {option.label}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        {selectedCity && cityProgress && (
                            <div className="text-sm text-muted-foreground mt-2">
                                Showing metrics for {cityOptions.find(c => c.value === selectedCity)?.label || selectedCity}
                            </div>
                        )}
                    </div>
                </CardContent>
            </Card>

            {/* KPI Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {/* Verified locations (Selected City) */}
                <Card className="rounded-2xl shadow-sm">
                    <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                        <CardTitle className="text-sm font-medium">
                            Verified {selectedCity ? `(${cityOptions.find(c => c.value === selectedCity)?.label || selectedCity})` : "(Rotterdam)"}
                        </CardTitle>
                        <MapPin className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        {loading ? (
                            <Skeleton className="h-8 w-16" />
                        ) : (
                            <>
                                <div className="text-2xl font-semibold">
                                    {verifiedCount}
                                </div>
                                {/* Filters in effect badge */}
                                <div className="mt-2 flex items-center gap-1">
                                    <span title="Verified locations must have: state=VERIFIED, confidence≥0.80, not retired, valid coordinates, and be within Rotterdam bbox. This matches the frontend map filter definition.">
                                        <Badge
                                            variant="outline"
                                            className="text-xs"
                                        >
                                            <Info className="h-3 w-3 mr-1" />
                                            Filters in effect
                                        </Badge>
                                    </span>
                                </div>
                            </>
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
                                {formatPercentFromFraction(coverageRatio)}
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
                                {formatPercentRaw(growthWeekly)}
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Conversion rate (14d) */}
                <Card className="rounded-2xl shadow-sm">
                    <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                        <CardTitle className="text-sm font-medium">Conversion rate (14d)</CardTitle>
                        <Gauge className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        {loading ? (
                            <Skeleton className="h-8 w-16" />
                        ) : (
                            <div className="text-2xl font-semibold">
                                {formatPercentFromFraction(conversionRate14d)}
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
                                {formatPercentFromFraction(taskErrorRate)}
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
                                {google429Last60m}
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Discovery new candidates */}
                <Card className="rounded-2xl shadow-sm">
                    <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                        <CardTitle className="text-sm font-medium">Discovery (weekly)</CardTitle>
                        <Database className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        {loading ? (
                            <Skeleton className="h-8 w-16" />
                        ) : (
                            <div className="text-2xl font-semibold">
                                {newCandidatesWeekly}
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
                                {formatLatency(latencyP50)} / {formatLatency(latencyAvg)} / {formatLatency(latencyMax)}
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Stale Candidates */}
                <Card className="rounded-2xl shadow-sm">
                    <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                        <CardTitle className="text-sm font-medium">Stale Candidates ({data?.staleCandidates?.daysThreshold || 7}d)</CardTitle>
                        <AlertTriangle className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        {loading ? (
                            <Skeleton className="h-8 w-16" />
                        ) : (
                            <>
                                <div className="text-2xl font-semibold">
                                    {data?.staleCandidates?.totalStale ?? 0}
                                </div>
                                {data?.staleCandidates && data.staleCandidates.totalStale > 0 && (
                                    <div className="mt-2 text-xs text-muted-foreground">
                                        {Object.entries(data.staleCandidates.bySource).length > 0 && (
                                            <div>By source: {Object.entries(data.staleCandidates.bySource).map(([src, cnt]) => `${src}: ${cnt}`).join(", ")}</div>
                                        )}
                                        {Object.entries(data.staleCandidates.byCity).length > 0 && (
                                            <div className="mt-1">By city: {Object.entries(data.staleCandidates.byCity).map(([city, cnt]) => `${city}: ${cnt}`).join(", ")}</div>
                                        )}
                                    </div>
                                )}
                                {data?.staleCandidates && data.staleCandidates.totalStale > 100 && (
                                    <div className="mt-2">
                                        <Badge variant="outline" className="bg-amber-100 text-amber-800 border-amber-200 text-xs">
                                            <AlertTriangle className="h-3 w-3 mr-1" />
                                            High stale count - check verify_locations worker
                                        </Badge>
                                    </div>
                                )}
                            </>
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

            {/* Worker controls */}
            <Card className="rounded-2xl shadow-sm">
                <CardHeader>
                    <CardTitle>Worker controls</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                        <div className="space-y-2">
                            <Label htmlFor="worker-bot">Bot</Label>
                            <Select
                                value={selectedBot ?? ALL_BOTS}
                                onValueChange={(next) =>
                                    setSelectedBot(next === ALL_BOTS ? undefined : next)
                                }
                            >
                                <SelectTrigger id="worker-bot">
                                    <SelectValue placeholder="All bots" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value={ALL_BOTS}>All bots</SelectItem>
                                    {botOptions.map((option) => (
                                        <SelectItem key={option.value} value={option.value}>
                                            {option.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="worker-city">City (optional)</Label>
                            <Select
                                value={selectedCity ?? ALL_CITIES}
                                onValueChange={(next) =>
                                    setSelectedCity(next === ALL_CITIES ? undefined : next)
                                }
                            >
                                <SelectTrigger id="worker-city">
                                    <SelectValue placeholder="All cities" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value={ALL_CITIES}>All cities</SelectItem>
                                    {cityOptions.map((option) => (
                                        <SelectItem key={option.value} value={option.value}>
                                            {option.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="worker-category">Category (optional)</Label>
                            <Select
                                value={
                                    categoryDisabled
                                        ? ALL_CATEGORIES
                                        : selectedCategory ?? ALL_CATEGORIES
                                }
                                onValueChange={(next) =>
                                    setSelectedCategory(
                                        next === ALL_CATEGORIES ? undefined : next
                                    )
                                }
                                disabled={categoriesLoading || categoryDisabled}
                            >
                                <SelectTrigger id="worker-category">
                                    <SelectValue
                                        placeholder={
                                            categoriesLoading
                                                ? "Loading..."
                                                : categoryDisabled
                                                    ? "N/A for monitor"
                                                    : "All categories"
                                        }
                                    />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value={ALL_CATEGORIES}>All categories</SelectItem>
                                    {categoriesLoading ? (
                                        <SelectItem value="loading" disabled>Loading categories...</SelectItem>
                                    ) : categorySelectOptions.length === 0 ? (
                                        <SelectItem value="none" disabled>No categories available</SelectItem>
                                    ) : (
                                        categorySelectOptions.map((option) => (
                                            <SelectItem key={option.key} value={option.key}>
                                                {option.label}
                                            </SelectItem>
                                        ))
                                    )}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-3">
                        <Button onClick={handleRunWorker} disabled={isRunningWorker}>
                            {isRunningWorker ? "Starting…" : "Run worker"}
                        </Button>
                        <span className="text-xs text-muted-foreground">
                            Triggers the selected bot and records progress in the worker_runs table.
                        </span>
                    </div>
                </CardContent>
            </Card>

            {/* Workers */}
            <Card className="rounded-2xl shadow-sm">
                <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                        <span>Workers</span>
                        <span className="text-xs text-muted-foreground">
                            Polling every {Math.round(pollIntervalMs / 1000)}s
                        </span>
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    {loading ? (
                        <div className="space-y-3">
                            <Skeleton className="h-5 w-36" />
                            <Skeleton className="h-32 w-full" />
                        </div>
                    ) : (
                        <div className="space-y-6">
                            <div>
                                <h3 className="mb-2 text-sm font-medium">Active runs</h3>
                                {hasActiveRuns ? (
                                    <div className="space-y-3">
                                        {activeRuns.map((run) => (
                                            <div
                                                key={run.id}
                                                role="button"
                                                tabIndex={0}
                                                className="rounded-lg border p-3 cursor-pointer hover:bg-muted/50 transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                                                onClick={() => {
                                                    console.log("[AdminWorkers] Run clicked", run);
                                                    setSelectedRun(run);
                                                }}
                                                onKeyDown={(e) => {
                                                    if (e.key === "Enter" || e.key === " ") {
                                                        e.preventDefault();
                                                        console.log("[AdminWorkers] Run clicked (keyboard)", run);
                                                        setSelectedRun(run);
                                                    }
                                                }}
                                            >
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
                                                <div className="mt-2">
                                                    <Progress value={run.progress ?? 0} />
                                                    <div className="mt-1 text-xs text-muted-foreground">
                                                        {run.progress ?? 0}%
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="text-xs text-muted-foreground">No pending or running worker runs.</div>
                                )}
                            </div>
                            <div>
                                <h3 className="mb-2 text-sm font-medium">Worker telemetry</h3>
                                {workerStatuses.length === 0 ? (
                                    <div className="text-sm text-muted-foreground">No worker telemetry available.</div>
                                ) : (
                                    <div className="overflow-x-auto">
                                        <table className="w-full text-sm">
                                            <thead>
                                                <tr className="border-b">
                                                    <th className="text-left p-2">Worker</th>
                                                    <th className="text-left p-2">Status</th>
                                                    <th className="text-left p-2">Last run</th>
                                                    <th className="text-left p-2">Duration</th>
                                                    <th className="text-left p-2">Processed</th>
                                                    <th className="text-left p-2">Errors</th>
                                                    <th className="text-left p-2">Quota</th>
                                                    <th className="text-left p-2">Notes</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {workerStatuses.map((worker) => {
                                                    const notePreview =
                                                        worker.notes && worker.notes.trim().length > 0
                                                            ? worker.notes.split("\n")[0]
                                                            : "–";
                                                    return (
                                                        <tr key={worker.id} className="border-b align-top">
                                                            <td className="p-2">
                                                                <div className="font-medium">{worker.label}</div>
                                                                <div className="text-xs text-muted-foreground">{worker.id}</div>
                                                            </td>
                                                            <td className="p-2">
                                                                {(() => {
                                                                    const isInteractive = worker.status === "warning" || worker.status === "error";
                                                                    return (
                                                                        <Badge
                                                                            variant="outline"
                                                                            className={cn(
                                                                                "text-xs font-medium px-2 py-1",
                                                                                WORKER_STATUS_BADGE_CLASSES[worker.status],
                                                                                isInteractive && "cursor-pointer hover:opacity-80"
                                                                            )}
                                                                            onClick={isInteractive ? () => setSelectedWorker(worker) : undefined}
                                                                            role={isInteractive ? "button" : undefined}
                                                                            aria-label={isInteractive ? `Show diagnosis for ${worker.label} (${worker.status})` : undefined}
                                                                        >
                                                                            {worker.status.toUpperCase()}
                                                                        </Badge>
                                                                    );
                                                                })()}
                                                            </td>
                                                            <td className="p-2">{formatLastRun(worker.lastRun)}</td>
                                                            <td className="p-2">{formatDurationSeconds(worker.durationSeconds)}</td>
                                                            <td className="p-2">{formatCountWithContext(worker.processedCount, worker.windowLabel)}</td>
                                                            <td className="p-2">{formatCountWithContext(worker.errorCount, worker.windowLabel)}</td>
                                                            <td className="p-2">{formatQuotaInfo(worker.quotaInfo ?? null)}</td>
                                                            <td className="p-2">
                                                                <span className="whitespace-pre-line">
                                                                    {notePreview}
                                                                </span>
                                                            </td>
                                                        </tr>
                                                    );
                                                })}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Location State Breakdown */}
            <Card className="rounded-2xl shadow-sm">
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Database className="h-5 w-5" />
                        Location State Breakdown
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    {locationStateMetrics ? (
                        <div className="space-y-4">
                            <div className="text-sm text-muted-foreground">
                                Total locations: <span className="font-semibold text-foreground">{locationStateMetrics.total}</span>
                            </div>
                            <div className="space-y-2">
                                {locationStateMetrics.by_state.map((bucket) => {
                                    const state = bucket.state;
                                    const count = bucket.count;
                                    const badgeClass =
                                        state === "VERIFIED"
                                            ? "bg-emerald-100 text-emerald-800 border-emerald-200 dark:bg-emerald-900 dark:text-emerald-200"
                                            : state === "PENDING_VERIFICATION"
                                                ? "bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-900 dark:text-amber-200"
                                                : state === "CANDIDATE"
                                                    ? "bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900 dark:text-blue-200"
                                                    : state === "RETIRED"
                                                        ? "bg-gray-100 text-gray-800 border-gray-200 dark:bg-gray-800 dark:text-gray-300"
                                                        : "bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300";
                                    return (
                                        <div key={state} className="flex items-center justify-between p-2 rounded-md border">
                                            <Badge className={cn("font-medium", badgeClass)}>
                                                {state}
                                            </Badge>
                                            <span className="text-sm font-semibold">{count}</span>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    ) : (
                        <div className="text-sm text-muted-foreground">
                            Failed to load location state metrics
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Category Health */}
            <Card className="rounded-2xl shadow-sm">
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Activity className="h-5 w-5" />
                        Category Health
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    {loadingCategoryHealth ? (
                        <div className="space-y-2">
                            <Skeleton className="h-6 w-32" />
                            <Skeleton className="h-48 w-full" />
                        </div>
                    ) : !categoryHealth || Object.keys(categoryHealth.categories).length === 0 ? (
                        <div className="text-sm text-muted-foreground">No category health data available</div>
                    ) : (
                        <CategoryHealthTable categoryHealth={categoryHealth} categoryOptions={categoryOptions} />
                    )}
                </CardContent>
            </Card>

            {/* Discovery KPIs */}
            <Card className="rounded-2xl shadow-sm">
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Database className="h-5 w-5" />
                        Discovery KPIs (Last 30 Days)
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    {loadingKPIs ? (
                        <div className="space-y-2">
                            <Skeleton className="h-6 w-32" />
                            <Skeleton className="h-48 w-full" />
                        </div>
                    ) : !discoveryKPIs || discoveryKPIs.daily.length === 0 ? (
                        <div className="text-sm text-muted-foreground">No discovery run data available</div>
                    ) : (
                        <div className="space-y-4">
                            {/* Totals summary */}
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                                <div>
                                    <div className="text-muted-foreground">Inserted</div>
                                    <div className="text-2xl font-semibold text-green-600">
                                        {discoveryKPIs.totals.inserted}
                                    </div>
                                </div>
                                <div>
                                    <div className="text-muted-foreground">Updated</div>
                                    <div className="text-2xl font-semibold text-blue-600">
                                        {discoveryKPIs.totals.updated_existing}
                                    </div>
                                </div>
                                <div>
                                    <div className="text-muted-foreground">Fuzzy Deduped</div>
                                    <div className="text-2xl font-semibold text-yellow-600">
                                        {discoveryKPIs.totals.deduped_fuzzy}
                                    </div>
                                </div>
                                <div>
                                    <div className="text-muted-foreground">Failed</div>
                                    <div className="text-2xl font-semibold text-red-600">
                                        {discoveryKPIs.totals.failed}
                                    </div>
                                </div>
                            </div>

                            {/* Simple table */}
                            <div className="overflow-x-auto">
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr className="border-b">
                                            <th className="text-left p-2">Day</th>
                                            <th className="text-right p-2">Inserted</th>
                                            <th className="text-right p-2">Updated</th>
                                            <th className="text-right p-2">Fuzzy Deduped</th>
                                            <th className="text-right p-2">Failed</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {discoveryKPIs.daily.slice(0, 14).map((day) => (
                                            <tr key={day.day} className="border-b">
                                                <td className="p-2">{day.day}</td>
                                                <td className="text-right p-2 text-green-600">{day.inserted}</td>
                                                <td className="text-right p-2 text-blue-600">{day.updated_existing}</td>
                                                <td className="text-right p-2 text-yellow-600">{day.deduped_fuzzy}</td>
                                                <td className="text-right p-2 text-red-600">{day.failed}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Worker Diagnosis Dialog */}
            <WorkerDiagnosisDialog
                worker={selectedWorker}
                open={selectedWorker !== null}
                onOpenChange={(open) => {
                    if (!open) {
                        setSelectedWorker(null);
                    }
                }}
            />
        </div>
    );
}


