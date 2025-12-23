import { useEffect, useState } from "react";
import { getMyActivitySummary, type ActivitySummaryResponse } from "@/lib/api";
import { cn } from "@/lib/ui/cn";

interface RhythmSectionProps {
  className?: string;
}

export function RhythmSection({ className }: RhythmSectionProps) {
  const [activity, setActivity] = useState<ActivitySummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchActivity() {
      try {
        setLoading(true);
        setError(null);
        const data = await getMyActivitySummary();
        setActivity(data);
      } catch (err) {
        console.error("Failed to fetch activity summary:", err);
        setError("Failed to load activity");
      } finally {
        setLoading(false);
      }
    }

    fetchActivity();
  }, []);

  if (loading) {
    return (
      <div className={cn("rounded-xl bg-surface-muted/50 p-6", className)}>
        <div className="space-y-1">
          <h2 className="text-lg font-gilroy font-medium text-foreground">
            Ritme
          </h2>
          <p className="text-sm text-muted-foreground">Laden...</p>
        </div>
      </div>
    );
  }

  if (error || !activity) {
    return null; // Don't show section if there's an error or no activity
  }

  const activeDays = activity.last_4_weeks_active_days || 0;
  const isRegular = activeDays >= 7; // Show "düzenli" if 7+ active days in last 4 weeks

  if (!isRegular) {
    return null; // Only show if user has been regular
  }

  // Create a simple visual indicator: 4 weeks x 7 days = 28 dots
  // For simplicity, we'll show a grid representation
  const weeks = 4;
  const daysPerWeek = 7;
  const totalDays = weeks * daysPerWeek;

  // Calculate which days were active (simplified - we don't have exact day-by-day data)
  // We'll show a visual representation based on active_days count
  const activeDayCount = Math.min(activeDays, totalDays);

  return (
    <div className={cn("rounded-xl bg-surface-muted/50 p-6", className)}>
      <div className="space-y-3">
        <div className="space-y-1">
          <h2 className="text-lg font-gilroy font-medium text-foreground">
            Ritme
          </h2>
          <p className="text-sm text-muted-foreground">
            Son 4 haftadır düzenli
          </p>
        </div>

        {/* Visual calendar grid: 4 weeks x 7 days */}
        <div className="flex flex-col gap-1">
          {Array.from({ length: weeks }).map((_, weekIndex) => (
            <div key={weekIndex} className="flex gap-1">
              {Array.from({ length: daysPerWeek }).map((_, dayIndex) => {
                const dayNumber = weekIndex * daysPerWeek + dayIndex;
                const isActive = dayNumber < activeDayCount;
                return (
                  <div
                    key={dayIndex}
                    className={cn(
                      "h-2 w-2 rounded-full",
                      isActive
                        ? "bg-primary"
                        : "bg-muted"
                    )}
                    aria-label={
                      isActive
                        ? `Day ${dayNumber + 1} active`
                        : `Day ${dayNumber + 1} inactive`
                    }
                  />
                );
              })}
            </div>
          ))}
        </div>

        <p className="text-xs text-muted-foreground">
          {activeDays} actieve dagen in de laatste 4 weken
        </p>
      </div>
    </div>
  );
}


