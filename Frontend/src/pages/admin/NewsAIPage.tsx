import NewsAIDiagnosticsPanel from "@/components/admin/NewsAIDiagnosticsPanel";

export default function NewsAIPage() {
  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">News AI Logs</h1>
        <p className="text-sm text-muted-foreground mt-1">
          View AI classification logs and diagnostics for news processing
        </p>
      </div>
      <NewsAIDiagnosticsPanel />
    </div>
  );
}


















