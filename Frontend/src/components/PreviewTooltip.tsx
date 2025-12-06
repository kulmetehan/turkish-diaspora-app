import { useEffect, useRef } from "react";

import type { LocationMarker } from "@/api/fetchLocations";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { buildRouteUrl } from "@/lib/urlBuilders";
import { cn } from "@/lib/ui/cn";

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
            className="tda-card w-[260px] rounded-3xl border border-white/10 bg-surface-raised/95 p-4 text-foreground shadow-soft backdrop-blur-xl outline-none focus-visible:ring-2 focus-visible:ring-brand-white/70"
            tabIndex={-1}
        >
            <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                    <h3 className="text-sm font-semibold text-foreground line-clamp-2">{location.name}</h3>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                        {(location.category_label || location.category) && (
                            <Badge variant="secondary" className="capitalize text-[10px]">
                                {location.category_label ?? location.category}
                            </Badge>
                        )}
                    </div>
                </div>
                <button
                    type="button"
                    className="rounded-full border border-white/10 p-1 text-brand-white/70 transition-colors hover:bg-white/10 hover:text-brand-white focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-brand-white/70"
                    aria-label="Sluit preview"
                    onClick={onRequestClose}
                >
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
            </div>

            {address && (
                <p className="mt-3 text-xs text-muted-foreground line-clamp-2">{address}</p>
            )}

            <div className="mt-4 flex flex-wrap gap-2">
                <Button
                    size="sm"
                    className="flex-1"
                    onClick={() => {
                        onRequestDetail();
                    }}
                >
                    Details
                </Button>
                <Button
                    asChild
                    size="sm"
                    variant="outline"
                    aria-label="Open route in Maps"
                >
                    <a href={routeUrl} target={routeUrl.startsWith("http") ? "_blank" : undefined} rel="noopener noreferrer">
                        Route
                    </a>
                </Button>
            </div>
        </div>
    );
}

