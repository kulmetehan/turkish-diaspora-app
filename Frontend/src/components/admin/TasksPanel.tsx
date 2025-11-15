import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { getTasks, type TaskItem, type TasksResponse } from "@/lib/apiAdmin";
import { useCallback, useEffect, useRef, useState } from "react";
import { AlertCircle, Info } from "lucide-react";

const STATUS_BADGE_CLASSES: Record<string, string> = {
    PENDING: "bg-yellow-100 text-yellow-800 border-yellow-200",
    PROCESSING: "bg-blue-100 text-blue-800 border-blue-200",
    COMPLETED: "bg-emerald-100 text-emerald-800 border-emerald-200",
    FAILED: "bg-red-100 text-red-800 border-red-200",
};

function formatTimestamp(value: string | null | undefined): string {
    if (!value) return "–";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return value;
    }
    return date.toLocaleString();
}

function formatStatus(value: string): string {
    return value.toUpperCase();
}

export default function TasksPanel() {
    const [data, setData] = useState<TasksResponse | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);
    const [taskTypeFilter, setTaskTypeFilter] = useState<string>("ALL");
    const [statusFilter, setStatusFilter] = useState<string>("ALL");
    const [limit, setLimit] = useState<number>(50);
    const [offset, setOffset] = useState<number>(0);
    const isMountedRef = useRef(false);

    const loadTasks = useCallback(async () => {
        try {
            setLoading(true);
            const params: {
                task_type?: string;
                status?: string;
                limit: number;
                offset: number;
            } = {
                limit,
                offset,
            };
            if (taskTypeFilter !== "ALL") {
                params.task_type = taskTypeFilter;
            }
            if (statusFilter !== "ALL") {
                params.status = statusFilter;
            }
            const res = await getTasks(params);
            if (!isMountedRef.current) return;
            setData(res);
            setError(null);
        } catch (e: any) {
            if (!isMountedRef.current) return;
            setError(e?.message || "Failed to load tasks");
        } finally {
            if (!isMountedRef.current) return;
            setLoading(false);
        }
    }, [taskTypeFilter, statusFilter, limit, offset]);

    useEffect(() => {
        isMountedRef.current = true;
        return () => {
            isMountedRef.current = false;
        };
    }, []);

    useEffect(() => {
        loadTasks();
    }, [loadTasks]);

    // Reset offset when filters change
    useEffect(() => {
        setOffset(0);
    }, [taskTypeFilter, statusFilter]);

    const taskTypes = data ? Object.keys(data.summary) : [];
    const summary = data?.summary || {};
    const items = data?.items || [];
    const total = data?.total || 0;

    const hasMore = offset + limit < total;
    const hasPrevious = offset > 0;

    return (
        <div className="space-y-4">
            <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 flex items-start gap-3">
                <Info className="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
                <div className="text-sm text-blue-900">
                    <p className="font-medium mb-1">About Tasks Queue</p>
                    <p className="mb-2">
                        MonitorBot creates VERIFICATION tasks for stale VERIFIED locations.
                    </p>
                    <p>
                        Currently there is no separate worker consuming tasks (unless implemented later), so a growing queue is expected until a consumer exists.
                    </p>
                </div>
            </div>

            {error && (
                <Card className="border-red-200 bg-red-50">
                    <CardContent className="pt-6">
                        <div className="flex items-center gap-2 text-red-800">
                            <AlertCircle className="h-5 w-5" />
                            <span>{error}</span>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Summary Cards */}
            {taskTypes.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    {taskTypes.map((type) => {
                        const s = summary[type];
                        if (!s) return null;
                        return (
                            <Card key={type}>
                                <CardHeader className="pb-2">
                                    <CardTitle className="text-sm font-medium text-muted-foreground">
                                        {type}
                                    </CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="space-y-2">
                                        <div className="flex justify-between items-center">
                                            <span className="text-sm">Pending</span>
                                            <Badge variant="outline" className={STATUS_BADGE_CLASSES.PENDING}>
                                                {s.pending}
                                            </Badge>
                                        </div>
                                        <div className="flex justify-between items-center">
                                            <span className="text-sm">Processing</span>
                                            <Badge variant="outline" className={STATUS_BADGE_CLASSES.PROCESSING}>
                                                {s.processing}
                                            </Badge>
                                        </div>
                                        <div className="flex justify-between items-center">
                                            <span className="text-sm">Completed</span>
                                            <Badge variant="outline" className={STATUS_BADGE_CLASSES.COMPLETED}>
                                                {s.completed}
                                            </Badge>
                                        </div>
                                        <div className="flex justify-between items-center">
                                            <span className="text-sm">Failed</span>
                                            <Badge variant="outline" className={STATUS_BADGE_CLASSES.FAILED}>
                                                {s.failed}
                                            </Badge>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        );
                    })}
                </div>
            )}

            {/* Filters */}
            <Card>
                <CardHeader>
                    <CardTitle>Tasks</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="flex gap-4 mb-4">
                        <div className="flex-1">
                            <label className="text-sm font-medium mb-2 block">Task Type</label>
                            <Select value={taskTypeFilter} onValueChange={setTaskTypeFilter}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="ALL">All Types</SelectItem>
                                    {taskTypes.map((type) => (
                                        <SelectItem key={type} value={type}>
                                            {type}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="flex-1">
                            <label className="text-sm font-medium mb-2 block">Status</label>
                            <Select value={statusFilter} onValueChange={setStatusFilter}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="ALL">All Statuses</SelectItem>
                                    <SelectItem value="PENDING">Pending</SelectItem>
                                    <SelectItem value="PROCESSING">Processing</SelectItem>
                                    <SelectItem value="COMPLETED">Completed</SelectItem>
                                    <SelectItem value="FAILED">Failed</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    {/* Tasks Table */}
                    {loading ? (
                        <div className="space-y-2">
                            <Skeleton className="h-10 w-full" />
                            <Skeleton className="h-10 w-full" />
                            <Skeleton className="h-10 w-full" />
                        </div>
                    ) : items.length === 0 ? (
                        <div className="text-center py-8 text-muted-foreground">
                            No tasks found.
                        </div>
                    ) : (
                        <>
                            <div className="rounded-md border overflow-auto">
                                <table className="w-full text-sm">
                                    <thead className="bg-muted/50 border-b">
                                        <tr>
                                            <th className="w-20 px-3 py-2 text-left font-medium">ID</th>
                                            <th className="w-32 px-3 py-2 text-left font-medium">Type</th>
                                            <th className="w-32 px-3 py-2 text-left font-medium">Status</th>
                                            <th className="w-40 px-3 py-2 text-left font-medium">Created</th>
                                            <th className="w-40 px-3 py-2 text-left font-medium">Last Attempted</th>
                                            <th className="w-24 px-3 py-2 text-left font-medium">Location ID</th>
                                            <th className="w-20 px-3 py-2 text-left font-medium">Attempts</th>
                                            <th className="px-3 py-2 text-left font-medium">Payload</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {items.map((item: TaskItem) => (
                                            <tr key={item.id} className="border-b hover:bg-muted/50">
                                                <td className="px-3 py-2 font-mono text-sm">
                                                    {item.id}
                                                </td>
                                                <td className="px-3 py-2">{item.task_type}</td>
                                                <td className="px-3 py-2">
                                                    <Badge
                                                        variant="outline"
                                                        className={
                                                            STATUS_BADGE_CLASSES[formatStatus(item.status)] ||
                                                            "bg-gray-100 text-gray-800 border-gray-200"
                                                        }
                                                    >
                                                        {formatStatus(item.status)}
                                                    </Badge>
                                                </td>
                                                <td className="px-3 py-2 text-sm">
                                                    {formatTimestamp(item.created_at)}
                                                </td>
                                                <td className="px-3 py-2 text-sm">
                                                    {formatTimestamp(item.last_attempted_at)}
                                                </td>
                                                <td className="px-3 py-2 font-mono text-sm">
                                                    {item.location_id || "–"}
                                                </td>
                                                <td className="px-3 py-2 text-sm">
                                                    {item.attempts}
                                                </td>
                                                <td className="px-3 py-2 text-sm text-muted-foreground max-w-md truncate font-mono text-xs">
                                                    {item.payload ? JSON.stringify(item.payload) : "–"}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>

                            {/* Pagination */}
                            <div className="flex items-center justify-between mt-4">
                                <div className="text-sm text-muted-foreground">
                                    Showing {offset + 1} to {Math.min(offset + limit, total)} of {total} tasks
                                </div>
                                <div className="flex gap-2">
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={() => setOffset(Math.max(0, offset - limit))}
                                        disabled={!hasPrevious || loading}
                                    >
                                        Previous
                                    </Button>
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={() => setOffset(offset + limit)}
                                        disabled={!hasMore || loading}
                                    >
                                        Next
                                    </Button>
                                </div>
                            </div>
                        </>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}

