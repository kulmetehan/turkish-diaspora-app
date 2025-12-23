import { useEffect, useState } from "react";
import { getMyRecognition, type RecognitionResponse } from "@/lib/api";
import { cn } from "@/lib/ui/cn";
import { Icon } from "@/components/Icon";

interface RecognitionSectionProps {
  className?: string;
}

export function RecognitionSection({ className }: RecognitionSectionProps) {
  const [recognition, setRecognition] = useState<RecognitionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchRecognition() {
      try {
        setLoading(true);
        setError(null);
        const data = await getMyRecognition();
        setRecognition(data);
      } catch (err) {
        console.error("Failed to fetch recognition:", err);
        setError("Failed to load recognition");
      } finally {
        setLoading(false);
      }
    }

    fetchRecognition();
  }, []);

  if (loading) {
    return (
      <div className={cn("rounded-xl bg-surface-muted/50 p-6", className)}>
        <div className="space-y-1">
          <h2 className="text-lg font-gilroy font-medium text-foreground">
            Erkenning
          </h2>
          <p className="text-sm text-muted-foreground">Laden...</p>
        </div>
      </div>
    );
  }

  if (error || !recognition) {
    return null; // Don't show section if there's an error
  }

  if (recognition.recognitions.length === 0) {
    return null; // Don't show section if no active recognitions
  }

  return (
    <div className={cn("rounded-xl bg-surface-muted/50 p-6", className)}>
      <div className="space-y-4">
        <div className="space-y-1">
          <h2 className="text-lg font-gilroy font-medium text-foreground">
            Erkenning
          </h2>
          <p className="text-sm text-muted-foreground">
            Je actieve erkenningen
          </p>
        </div>

        <div className="space-y-2">
          {recognition.recognitions.map((entry, index) => (
            <div
              key={`${entry.category}-${entry.rank}-${index}`}
              className="flex items-start gap-2 p-3 rounded-lg bg-muted/30 border border-primary/20"
            >
              <Icon name="Award" className="h-5 w-5 text-primary mt-0.5 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground">
                  {entry.title}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Rank #{entry.rank}
                  {entry.context && ` · ${entry.context}`}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}


