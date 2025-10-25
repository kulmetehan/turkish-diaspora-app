// Frontend/src/lib/map/marker-icons.tsx
import type { LocationMarker } from "@/api/fetchLocations";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils"; // uit je design system (shadcn helper)
import { AlertTriangle, CheckCircle2, CircleDot, Clock } from "lucide-react";

type Props = { loc: LocationMarker; selected?: boolean };

export function MarkerIcon({ loc, selected }: Props) {
  const status = loc.state;
  const color =
    status === "VERIFIED" ? "bg-emerald-600" :
      status === "PENDING_VERIFICATION" ? "bg-amber-500" :
        status === "SUSPENDED" ? "bg-rose-600" :
          status === "RETIRED" ? "bg-gray-400" : "bg-sky-600";

  const Icon =
    status === "VERIFIED" ? CheckCircle2 :
      status === "PENDING_VERIFICATION" ? Clock :
        status === "SUSPENDED" ? AlertTriangle :
          CircleDot;

  return (
    <div className={cn(
      "rounded-full text-white shadow-lg border border-white/60",
      color,
      selected ? "ring-2 ring-black/20 scale-105" : "ring-1 ring-black/10",
      "transition-transform will-change-transform"
    )} style={{ width: 28, height: 28, display: "grid", placeItems: "center" }}>
      <Icon size={16} />
      <span className="sr-only">{loc.name}</span>
    </div>
  );
}

export function MarkerBadge({ loc }: { loc: LocationMarker }) {
  const tone =
    loc.state === "VERIFIED" ? "default" :
      loc.state === "PENDING_VERIFICATION" ? "secondary" : "outline";
  return <Badge variant={tone as any}>{loc.category}</Badge>;
}
