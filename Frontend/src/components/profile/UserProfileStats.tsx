import { Card } from "@/components/ui/card";
import { type UserStats } from "@/lib/api";

export function UserProfileStats({ stats }: { stats: UserStats }) {
  return (
    <Card className="p-3">
      <div className="grid grid-cols-4 gap-4 text-center">
        <div>
          <div className="text-2xl font-bold text-red-500">{stats.check_ins_count}</div>
          <div className="text-xs text-muted-foreground">Check-ins</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-red-500">{stats.notes_count}</div>
          <div className="text-xs text-muted-foreground">Notities</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-red-500">{stats.favorites_count}</div>
          <div className="text-xs text-muted-foreground">Favorieten</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-red-500">{stats.reactions_count}</div>
          <div className="text-xs text-muted-foreground">Reacties</div>
        </div>
      </div>
    </Card>
  );
}

