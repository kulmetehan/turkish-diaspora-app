import { Suspense } from "react";
import TasksPanel from "@/components/admin/TasksPanel";

export default function TasksPage() {
  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Tasks</h1>
        <p className="text-sm text-muted-foreground mt-1">
          View and manage background tasks and queues
        </p>
      </div>
      <Suspense fallback={<div className="text-sm text-muted-foreground p-4">Loading tasks…</div>}>
        <TasksPanel />
      </Suspense>
    </div>
  );
}







