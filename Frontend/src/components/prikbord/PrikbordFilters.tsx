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

interface PrikbordFiltersProps {
    filters: SharedLinkFilters;
    onFiltersChange: (filters: SharedLinkFilters) => void;
}

export function PrikbordFilters({
    filters,
    onFiltersChange,
}: PrikbordFiltersProps) {
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
            >
                <SelectTrigger className="w-[100px] h-8 text-xs">
                    <SelectValue placeholder="Platform" />
                </SelectTrigger>
                <SelectContent>
                    <SelectItem value="all" className="text-xs">Alles</SelectItem>
                    {Object.entries(PLATFORM_LABELS).map(([value, label]) => (
                        <SelectItem key={value} value={value} className="text-xs">
                            {label}
                        </SelectItem>
                    ))}
                </SelectContent>
            </Select>
        </div>
    );
}

