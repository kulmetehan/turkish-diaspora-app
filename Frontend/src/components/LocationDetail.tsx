import type { LocationMarker } from "@/api/fetchLocations";
import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

type Props = {
    location: LocationMarker;
    onBackToList: () => void;
};

export default function LocationDetail({ location, onBackToList }: Props) {
    return (
        <div className="flex flex-col h-full">
            {/* Header with back button */}
            <div className="flex items-center gap-3 p-4 border-b bg-background">
                <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        onBackToList();
                    }}
                    className="flex items-center gap-2"
                >
                    <Icon name="ArrowLeft" className="h-4 w-4" />
                    Back to List
                </Button>
                <div className="flex-1" />
            </div>

            {/* Location content */}
            <div className="flex-1 overflow-auto p-4">
                <Card className="p-4 mb-4">
                    <div className="space-y-3">
                        {/* Name */}
                        <div className="flex items-start justify-between">
                            <h2 className="text-xl font-semibold">{location.name}</h2>
                            {/* rating removed */}
                        </div>

                        {/* Category */}
                        {(location.category_label || location.category) && (
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                <Icon name="Tag" className="h-4 w-4" />
                                <span className="capitalize">{location.category_label ?? location.category}</span>
                            </div>
                        )}

                        {/* Turkish indicator */}
                        {location.is_turkish && (
                            <div className="flex items-center gap-2 text-sm text-emerald-700">
                                <Icon name="CheckCircle" className="h-4 w-4" />
                                <span>Turkish Business</span>
                            </div>
                        )}

                        {/* Confidence score */}
                        {typeof location.confidence_score === "number" && (
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                <Icon name="Target" className="h-4 w-4" />
                                <span>AI Confidence: {(location.confidence_score * 100).toFixed(0)}%</span>
                            </div>
                        )}

                        {/* State */}
                        {location.state && (
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                <Icon name="MapPin" className="h-4 w-4" />
                                <span className="capitalize">{location.state}</span>
                            </div>
                        )}
                    </div>
                </Card>

                {/* Future enhancements placeholder */}
                <Card className="p-4">
                    <div className="space-y-2">
                        <h3 className="font-medium text-sm text-muted-foreground">Future Features</h3>
                        <div className="text-sm text-muted-foreground">
                            <p>• Address and contact information</p>
                            <p>• Directions and distance</p>
                            {/* reviews removed */}
                            <p>• Opening hours</p>
                        </div>
                    </div>
                </Card>
            </div>
        </div>
    );
}
