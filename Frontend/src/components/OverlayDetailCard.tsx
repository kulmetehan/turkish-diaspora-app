import { useMemo } from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";

import type { LocationMarker } from "@/api/fetchLocations";
import { Icon } from "@/components/Icon";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useViewportContext } from "@/contexts/viewport";
import { buildGoogleSearchUrl, buildRouteUrl, deriveCityForLocation } from "@/lib/urlBuilders";
import { cn } from "@/lib/ui/cn";

type OverlayDetailCardProps = {
    location: LocationMarker;
    open: boolean;
    onClose: () => void;
};

function safeString(value: unknown): string | null {
    if (typeof value !== "string") return null;
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
}

export default function OverlayDetailCard({ location, open, onClose }: OverlayDetailCardProps) {
    const { viewport } = useViewportContext();
    const city = useMemo(() => deriveCityForLocation(location, "Unknown"), [location]);

    const routeUrl = useMemo(() => buildRouteUrl(location), [location]);
    const googleSearchUrl = useMemo(
        () =>
            buildGoogleSearchUrl(location.name, location.city, {
                loc: location,
                viewport,
            }),
        [location, viewport]
    );

    const routeLinkProps = useMemo(() => {
        const isWebTarget = routeUrl.startsWith("http");
        return {
            target: isWebTarget ? "_blank" : undefined,
            rel: isWebTarget ? "noopener noreferrer" : undefined,
        } as const;
    }, [routeUrl]);

    const googleLinkProps = useMemo(
        () => ({
            target: "_blank" as const,
            rel: "noopener noreferrer" as const,
        }),
        []
    );

    const categoryLabel = safeString(location.category_label) ?? safeString(location.category) ?? null;
    const address = safeString(location.address);

    const confidenceDisplay =
        typeof location.confidence_score === "number"
            ? `${Math.round(location.confidence_score * 100)}%`
            : null;

    return (
        <DialogPrimitive.Root open={open} onOpenChange={(next) => { if (!next) onClose(); }}>
            <DialogPrimitive.Portal>
                <DialogPrimitive.Overlay className="fixed inset-0 z-[55] bg-black/20 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:animate-in data-[state=open]:fade-in-0" />
                <DialogPrimitive.Content
                    className={cn(
                        "fixed inset-x-0 bottom-0 top-auto z-[60] mx-auto w-full max-w-screen-sm",
                        "flex max-h-[min(70vh,560px)] flex-col rounded-t-3xl border border-border/80 bg-background text-foreground shadow-2xl",
                        "px-5 pt-6 pb-[calc(env(safe-area-inset-bottom)+20px)]",
                        "focus:outline-none data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:slide-in-from-bottom",
                        "data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:slide-out-to-bottom",
                        "lg:left-1/2 lg:right-auto lg:top-1/2 lg:bottom-auto lg:max-h-[85vh] lg:w-[min(90vw,840px)] lg:max-w-[min(90vw,840px)] lg:-translate-x-1/2 lg:-translate-y-1/2",
                        "lg:rounded-2xl lg:px-6 lg:pb-6 lg:shadow-2xl",
                        "lg:data-[state=open]:zoom-in-95 lg:data-[state=closed]:zoom-out-95"
                    )}
                    aria-labelledby="overlay-detail-title"
                    aria-describedby="overlay-detail-description"
                >
                    <header className="flex flex-col gap-4 border-b pb-4 lg:flex-row lg:items-start lg:justify-between">
                        <div className="min-w-0 flex-1 space-y-3">
                            <DialogPrimitive.Title
                                id="overlay-detail-title"
                                className="truncate text-2xl font-semibold tracking-tight"
                            >
                                {location.name}
                            </DialogPrimitive.Title>
                            <div className="flex flex-wrap items-center gap-2">
                                {categoryLabel && (
                                    <Badge variant="secondary" className="capitalize">
                                        {categoryLabel}
                                    </Badge>
                                )}
                                {location.is_turkish && (
                                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
                                        <Icon name="CheckCircle" className="h-3.5 w-3.5" />
                                        Turkish owned
                                    </span>
                                )}
                                {confidenceDisplay && (
                                    <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                                        <Icon name="Target" className="h-3.5 w-3.5" />
                                        {confidenceDisplay} confidence
                                    </span>
                                )}
                            </div>
                        </div>
                        <div className="flex items-center gap-2 self-end lg:self-auto">
                            <Button
                                asChild
                                variant="outline"
                                size="icon"
                                aria-label="Open route in Maps"
                                title="Open route in Maps"
                            >
                                <a href={routeUrl} {...routeLinkProps}>
                                    <Icon name="Navigation" className="h-4 w-4" />
                                </a>
                            </Button>
                            <Button
                                asChild
                                variant="outline"
                                size="icon"
                                aria-label="Search on Google"
                                title="Search on Google"
                            >
                                <a href={googleSearchUrl} {...googleLinkProps}>
                                    <Icon name="Search" className="h-4 w-4" />
                                </a>
                            </Button>
                            <DialogPrimitive.Close
                                className="ml-1 rounded-full border border-transparent p-2 text-muted-foreground transition hover:border-border hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                                aria-label="Close details"
                            >
                                <Icon name="X" className="h-4 w-4" />
                            </DialogPrimitive.Close>
                        </div>
                    </header>

                    <div
                        id="overlay-detail-description"
                        className="mt-4 flex-1 overflow-y-auto"
                    >
                        <div className="space-y-5">
                            {address && (
                                <Card className="p-4">
                                    <div className="flex items-start gap-3">
                                        <Icon name="MapPin" className="mt-0.5 h-4 w-4 text-muted-foreground" />
                                        <div>
                                            <p className="text-sm font-medium text-muted-foreground">Address</p>
                                            <p className="mt-1 text-sm leading-snug">{address}</p>
                                        </div>
                                    </div>
                                </Card>
                            )}

                            <Card className="p-4">
                                <div className="space-y-3 text-sm text-muted-foreground">
                                    <div className="flex items-center gap-3">
                                        <Icon name="Tags" className="h-4 w-4" />
                                        <span>
                                            Category:{" "}
                                            <span className="font-medium text-foreground">
                                                {categoryLabel ?? "Unknown"}
                                            </span>
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <Icon name="Map" className="h-4 w-4" />
                                        <span>
                                            City: <span className="font-medium text-foreground">{city}</span>
                                        </span>
                                    </div>
                                    {location.state && (
                                        <div className="flex items-center gap-3">
                                            <Icon name="Shield" className="h-4 w-4" />
                                            <span>
                                                Verification state:{" "}
                                                <span className="font-medium text-foreground capitalize">
                                                    {location.state.toLowerCase()}
                                                </span>
                                            </span>
                                        </div>
                                    )}
                                </div>
                            </Card>
                        </div>
                    </div>
                </DialogPrimitive.Content>
            </DialogPrimitive.Portal>
        </DialogPrimitive.Root>
    );
}

