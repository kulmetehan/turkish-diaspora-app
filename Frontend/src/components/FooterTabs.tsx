import { forwardRef, type ComponentProps, type CSSProperties } from "react";
import { NavLink } from "react-router-dom";

import { Icon } from "@/components/Icon";
import { cn } from "@/lib/ui/cn";

type TabConfig = {
  to: string;
  icon: ComponentProps<typeof Icon>["name"];
  label: string;
  end?: boolean;
};

const tabs: TabConfig[] = [
  { to: "/feed", icon: "Sparkles", label: "Feed" },
  { to: "/news", icon: "Newspaper", label: "News" },
  { to: "/map", icon: "Map", label: "Map", end: true },
  { to: "/events", icon: "CalendarCheck", label: "Events" },
  { to: "/account", icon: "User2", label: "Account" },
];

export const FooterTabs = forwardRef<HTMLDivElement, ComponentProps<"div">>(
  function FooterTabs({ className, style, ...props }, ref) {
    const height = "84px";
    const combinedStyle = {
      height,
      "--footer-height": height,
      ...style,
    } as CSSProperties & { "--footer-height"?: string };
    return (
      <div
        ref={ref}
        style={combinedStyle}
        className={cn(
          "fixed bottom-0 inset-x-0 z-50 border-t border-border bg-background/95 pb-[env(safe-area-inset-bottom)] shadow-lg",
          "supports-[backdrop-filter]:bg-background/80 backdrop-blur",
          className,
        )}
        {...props}
      >
        <nav
          aria-label="Primary navigation"
          className="mx-auto flex w-full max-w-3xl items-center justify-around px-3 py-2 md:gap-2"
        >
          {tabs.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
              end={tab.end}
              className={({ isActive }) =>
                cn(
                  "group flex flex-1 flex-col items-center justify-center gap-1 rounded-xl px-2 py-2 text-xs font-medium text-muted-foreground transition",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                  "min-h-[56px]",
                  isActive && "text-primary",
                )
              }
              aria-label={`${tab.label} tab`}
            >
              {({ isActive }) => (
                <>
                  <span
                    data-active={isActive ? "true" : "false"}
                    className={cn(
                      "flex h-10 w-10 items-center justify-center rounded-full transition",
                      isActive ? "bg-primary/10 text-primary" : "bg-transparent text-muted-foreground",
                    )}
                  >
                    <Icon name={tab.icon} sizeRem={1.35} aria-hidden />
                  </span>
                  <span className="leading-none">{tab.label}</span>
                </>
              )}
            </NavLink>
          ))}
        </nav>
      </div>
    );
  },
);

