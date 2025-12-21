// Frontend/src/components/account/AccountTabs.tsx
import { cn } from "@/lib/ui/cn";

export type AccountTabKey = "weergave" | "privacy" | "notificaties" | "referral" | "geschiedenis";

export interface AccountTabsProps {
  value: AccountTabKey;
  onChange: (next: AccountTabKey) => void;
  className?: string;
}

const TABS: Array<{ label: string; value: AccountTabKey }> = [
  { label: "Algemeen", value: "weergave" },
  { label: "Privacy", value: "privacy" },
  { label: "Notificaties", value: "notificaties" },
  { label: "Referral", value: "referral" },
  { label: "Geschiedenis", value: "geschiedenis" },
];

export function AccountTabs({ value, onChange, className }: AccountTabsProps) {
  return (
    <div
      className={cn(
        "flex gap-2 overflow-x-auto px-4 py-2",
        className
      )}
      style={{
        scrollbarWidth: "none", // Firefox
        msOverflowStyle: "none", // IE/Edge
      }}
    >
      {TABS.map((tab) => {
        const isActive = value === tab.value;
        return (
          <button
            key={tab.value}
            type="button"
            onClick={() => onChange(tab.value)}
            className={cn(
              "flex-shrink-0 rounded-sm px-4 py-1.5 text-sm font-gilroy font-medium transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2",
              isActive
                ? "bg-primary text-primary-foreground shadow-soft"
                : "bg-gray-100 text-black hover:bg-gray-200"
            )}
            aria-pressed={isActive}
            aria-label={`Filter by ${tab.label}`}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
