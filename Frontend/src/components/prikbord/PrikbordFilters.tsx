// Frontend/src/components/prikbord/PrikbordFilters.tsx
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import type { Platform, SharedLinkFilters } from "@/types/prikbord";
import { PLATFORM_LABELS } from "@/types/prikbord";
import { getAvailablePlatforms } from "@/lib/api/prikbord";
import { useEffect, useState } from "react";

interface PrikbordFiltersProps {
    filters: SharedLinkFilters;
    onFiltersChange: (filters: SharedLinkFilters) => void;
}

export function PrikbordFilters({
    filters,
    onFiltersChange,
}: PrikbordFiltersProps) {
    const [availablePlatforms, setAvailablePlatforms] = useState<Platform[]>([]);
    const [isLoadingPlatforms, setIsLoadingPlatforms] = useState(true);

    useEffect(() => {
        // Fetch available platforms on mount
        getAvailablePlatforms()
            .then((platforms) => {
                setAvailablePlatforms(platforms as Platform[]);
                setIsLoadingPlatforms(false);
            })
            .catch((err) => {
                console.error("Failed to load available platforms:", err);
                setIsLoadingPlatforms(false);
            });
    }, []);

    const handlePlatformChange = (platform: string) => {
        onFiltersChange({
            ...filters,
            platform: platform === "all" ? undefined : (platform as Platform),
        });
    };

    const handlePostTypeChange = (postType: string) => {
        onFiltersChange({
            ...filters,
            post_type: postType === "all" ? undefined : (postType as "link" | "media"),
        });
    };

    return (
        <div className="flex items-center gap-2">
            <Select
                value={filters.post_type || "all"}
                onValueChange={handlePostTypeChange}
            >
                <SelectTrigger className="w-[90px] h-8 text-xs">
                    <SelectValue placeholder="Type" />
                </SelectTrigger>
                <SelectContent>
                    <SelectItem value="all" className="text-xs">Alles</SelectItem>
                    <SelectItem value="link" className="text-xs">Links</SelectItem>
                    <SelectItem value="media" className="text-xs">Media</SelectItem>
                </SelectContent>
            </Select>
            <Select
                value={filters.platform || "all"}
                onValueChange={handlePlatformChange}
                disabled={isLoadingPlatforms}
            >
                <SelectTrigger className="w-[100px] h-8 text-xs">
                    <SelectValue placeholder="Platform" />
                </SelectTrigger>
                <SelectContent>
                    <SelectItem value="all" className="text-xs">Alles</SelectItem>
                    {availablePlatforms.map((platform) => (
                        <SelectItem key={platform} value={platform} className="text-xs">
                            {PLATFORM_LABELS[platform] || platform}
                        </SelectItem>
                    ))}
                </SelectContent>
            </Select>
        </div>
    );
}

