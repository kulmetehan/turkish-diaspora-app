import { useEffect, useRef } from "react";

import type { LocationMarker } from "@/api/fetchLocations";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/ui/cn";
import { buildRouteUrl } from "@/lib/urlBuilders";

type PreviewTooltipProps = {
    location: LocationMarker;
    onRequestDetail: () => void;
    onRequestClose: () => void;
};

export default function PreviewTooltip({ location, onRequestDetail, onRequestClose }: PreviewTooltipProps) {
    const containerRef = useRef<HTMLDivElement | null>(null);

    useEffect(() => {
        const handler = (event: KeyboardEvent) => {
            if (event.key === "Escape") {
                event.preventDefault();
                onRequestClose();
            }
        };
        window.addEventListener("keydown", handler);
        return () => {
            window.removeEventListener("keydown", handler);
        };
    }, [onRequestClose]);

    const routeUrl = buildRouteUrl(location);
    const address = typeof location.address === "string" && location.address.trim() ? location.address.trim() : null;

    return (
        <div
            ref={containerRef}
            role="dialog"
            aria-modal="false"
            aria-label={`Preview voor ${location.name}`}
            className="tda-card w-[260px] rounded-3xl border border-brand-red p-4 text-foreground shadow-lg shadow-gray-500/20 backdrop-blur-xl outline-none focus-visible:ring-2 focus-visible:ring-brand-white/70 relative overflow-hidden"
            style={{
                background: 'linear-gradient(180deg, hsl(var(--brand-red) / 0.20) 0%, hsl(var(--brand-red) / 0.10) 50%, transparent 100%), hsl(var(--surface-raised) / 0.95)',
            }}
            tabIndex={-1}
        >
            <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                    <h3 className="text-sm font-gilroy font-semibold text-foreground line-clamp-2">{location.name}</h3>
                </div>
                <div className="flex items-start gap-2 flex-shrink-0">
                    {(location.category_label || location.category) && (
                        <Badge variant="secondary" className="capitalize text-[10px] font-gilroy">
                            {location.category_label ?? location.category}
                        </Badge>
                    )}
                    <button
                        type="button"
                        className="rounded-full border border-white/10 p-1 text-gray-600 transition-colors hover:bg-white/10 hover:text-gray-800 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-brand-white/70 flex-shrink-0"
                        aria-label="Sluit preview"
                        onClick={onRequestClose}
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>
            </div>

            {address && (
                <p className="mt-3 text-xs font-gilroy font-normal text-muted-foreground line-clamp-2">{address}</p>
            )}

            <div className="mt-4 flex flex-wrap gap-2">
                <button
                    type="button"
                    onClick={() => {
                        onRequestDetail();
                    }}
                    className={cn(
                        "flex-shrink-0 rounded-sm px-3 py-1 text-xs font-gilroy font-medium transition-all",
                        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2",
                        "bg-primary/90 text-primary-foreground shadow-soft",
                        "hover:bg-gradient-to-r hover:from-primary/90 hover:to-primary/70"
                    )}
                >
                    Details
                </button>
                <button
                    type="button"
                    onClick={() => {
                        if (routeUrl.startsWith("http")) {
                            window.open(routeUrl, "_blank", "noopener,noreferrer");
                        } else {
                            window.location.href = routeUrl;
                        }
                    }}
                    aria-label="Open route in Maps"
                    className={cn(
                        "flex-shrink-0 rounded-sm px-3 py-1 text-xs font-gilroy font-medium transition-colors",
                        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2",
                        "bg-gray-600/80 text-white/90 hover:bg-gray-400/80 hover:text-white"
                    )}
                >
                    Route
                </button>
            </div>
        </div>
    );
}

