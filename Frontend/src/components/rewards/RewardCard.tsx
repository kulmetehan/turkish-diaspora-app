// Frontend/src/components/rewards/RewardCard.tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { UserReward } from "@/lib/api";
import { cn } from "@/lib/ui/cn";
import { Gift } from "lucide-react";

export interface RewardCardProps {
  reward: UserReward;
  className?: string;
}

export function RewardCard({ reward, className }: RewardCardProps) {
  return (
    <Card className={cn("mb-4", className)}>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Gift className="h-5 w-5 text-primary" />
          <CardTitle className="text-lg font-gilroy font-semibold">
            {reward.reward.title}
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {reward.reward.description && (
            <p className="text-sm text-muted-foreground">
              {reward.reward.description}
            </p>
          )}
          <p className="text-sm font-medium">
            Van: {reward.reward.sponsor}
          </p>
          <div className="flex items-center gap-2 mt-3">
            <span
              className={cn(
                "text-xs px-2 py-1 rounded-full",
                reward.status === "pending"
                  ? "bg-primary/10 text-primary"
                  : reward.status === "claimed"
                  ? "bg-green-500/10 text-green-600"
                  : "bg-muted text-muted-foreground"
              )}
            >
              {reward.status === "pending"
                ? "Nog niet geclaimed"
                : reward.status === "claimed"
                ? "Geclaimed"
                : reward.status}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}


