// Frontend/src/components/onecikanlar/LeaderboardCards.tsx
import { LeaderboardCard } from "./LeaderboardCard";
import type { LeaderboardCard as LeaderboardCardType } from "@/lib/api";
import { cn } from "@/lib/ui/cn";

export interface LeaderboardCardsProps {
  cards: LeaderboardCardType[];
  onUserClick?: (userId: string) => void;
  className?: string;
}

export function LeaderboardCards({
  cards,
  onUserClick,
  className,
}: LeaderboardCardsProps) {
  if (cards.length === 0) {
    return (
      <div className={cn("text-center py-8", className)}>
        <p className="text-muted-foreground">
          Geen leaderboard data beschikbaar voor deze periode.
        </p>
      </div>
    );
  }

  return (
    <div className={cn("space-y-4", className)}>
      {cards.map((card) => (
        <LeaderboardCard
          key={card.category}
          card={card}
          onUserClick={onUserClick}
        />
      ))}
    </div>
  );
}


