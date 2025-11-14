import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getDiscoveryGrid, getMetricsSnapshot, type MetricsSnapshot } from "@/lib/api";

export default function DiscoveryCoverageSummary() {
  const [metrics, setMetrics] = useState<MetricsSnapshot | null>(null);
  const [gridData, setGridData] = useState<Awaited<ReturnType<typeof getDiscoveryGrid>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [metricsData, gridDataResult] = await Promise.all([
          getMetricsSnapshot(),
          getDiscoveryGrid("rotterdam"),
        ]);
        setMetrics(metricsData);
        setGridData(gridDataResult);
      } catch (err) {
        console.error("Failed to fetch summary data:", err);
        // Handle timeout specifically
        if (err instanceof Error && err.message.includes("timeout")) {
          setError("The request timed out. Please try again.");
        } else {
          setError(err instanceof Error ? err.message : "Failed to load data");
        }
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Discovery Coverage Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">Loading...</div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Discovery Coverage Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-red-600">Error: {error}</div>
        </CardContent>
      </Card>
    );
  }

  // Calculate coverage ratio
  const totalCells = gridData?.length || 0;
  const visitedCells = gridData?.filter((cell) => cell.calls > 0).length || 0;
  const coverageRatio = totalCells > 0 ? (visitedCells / totalCells) * 100 : 0;

  // Get 30-day discovery stats from metrics
  const discoveryMetrics = metrics?.discovery;
  const weeklyCandidates = discoveryMetrics?.newCandidatesPerWeek || 0;
  // Estimate 30-day inserts (roughly 4 weeks)
  const estimated30DayInserts = weeklyCandidates * 4;

  // Get updates and dedupes from latest discovery run (if available)
  const discoveryWorker = metrics?.workers.find((w) => w.id === "discovery_bot");
  const lastRunNotes = discoveryWorker?.notes || "";

  // Extract stats from grid data
  const totalInserts = gridData?.reduce((sum, cell) => sum + cell.inserts, 0) || 0;
  const totalCalls = gridData?.reduce((sum, cell) => sum + cell.calls, 0) || 0;
  const totalErrors = gridData?.reduce((sum, cell) => sum + cell.error429 + cell.errorOther, 0) || 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Discovery Coverage Summary</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <div className="text-sm font-medium text-muted-foreground">Coverage Ratio</div>
          <div className="text-2xl font-bold">{coverageRatio.toFixed(1)}%</div>
          <div className="text-xs text-muted-foreground mt-1">
            {visitedCells} of {totalCells} grid cells visited
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-sm font-medium text-muted-foreground">Total Inserts (30d)</div>
            <div className="text-xl font-semibold">{totalInserts}</div>
          </div>
          <div>
            <div className="text-sm font-medium text-muted-foreground">Total Calls</div>
            <div className="text-xl font-semibold">{totalCalls.toLocaleString()}</div>
          </div>
        </div>

        <div>
          <div className="text-sm font-medium text-muted-foreground">Error Rate</div>
          <div className="text-xl font-semibold">
            {totalCalls > 0 ? ((totalErrors / totalCalls) * 100).toFixed(2) : 0}%
          </div>
          <div className="text-xs text-muted-foreground mt-1">
            {totalErrors} errors out of {totalCalls.toLocaleString()} calls
          </div>
        </div>

        <div className="pt-2 border-t">
          <div className="text-sm text-muted-foreground">
            {coverageRatio > 80 ? (
              <>
                Most grid cells in Rotterdam have already been explored, so recent discovery runs
                mainly update existing locations instead of finding new ones.
              </>
            ) : coverageRatio > 50 ? (
              <>
                A significant portion of Rotterdam has been covered. Discovery runs are finding
                both new locations and updating existing ones.
              </>
            ) : (
              <>
                Discovery coverage is still expanding across Rotterdam. Recent runs are actively
                finding new locations in unexplored areas.
              </>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

