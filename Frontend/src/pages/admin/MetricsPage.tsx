import { Suspense } from "react";
import MetricsDashboard from "@/components/admin/MetricsDashboard";

export default function MetricsPage() {
  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Metrics</h1>
        <p className="text-sm text-muted-foreground mt-1">
          System metrics, worker status, and performance indicators
        </p>
      </div>
      <Suspense fallback={<div className="text-sm text-muted-foreground p-4">Loading metrics…</div>}>
        <MetricsDashboard />
      </Suspense>
    </div>
  );
}

















