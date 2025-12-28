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

    return (
        <div className="flex items-center gap-2">
            <Select
                value={filters.platform || "all"}
                onValueChange={handlePlatformChange}
            >
                <SelectTrigger className="w-[140px]">
                    <SelectValue placeholder="Platform" />
                </SelectTrigger>
                <SelectContent>
                    <SelectItem value="all">Alle platforms</SelectItem>
                    {Object.entries(PLATFORM_LABELS).map(([value, label]) => (
                        <SelectItem key={value} value={value}>
                            {label}
                        </SelectItem>
                    ))}
                </SelectContent>
            </Select>
        </div>
    );
}

