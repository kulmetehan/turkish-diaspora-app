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
  { to: "/feed", icon: "MoonStar", label: "FEED" },
  { to: "/news", icon: "Newspaper", label: "NIEUWS" },
  { to: "/map", icon: "Map", label: "KAART", end: true },
  { to: "/events", icon: "CalendarCheck", label: "Events" },
  { to: "/account", icon: "User2", label: "Account" },
];

export const FooterTabs = forwardRef<HTMLDivElement, ComponentProps<"div">>(
  function FooterTabs({ className, style, ...props }, ref) {
    const height = "72px";
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
          "fixed inset-x-0 bottom-0 z-50 border-t border-border bg-nav/95 pb-[env(safe-area-inset-bottom)] text-foreground shadow-[0_-12px_30px_rgba(15,23,42,0.08)]",
          className,
        )}
        {...props}
      >
        <nav
          aria-label="Primary navigation"
          className="mx-auto flex w-full max-w-3xl items-center justify-around px-3 pt-1 pb-2 md:gap-2"
        >
          {tabs.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
              end={tab.end}
              className={({ isActive }) =>
                cn(
                  "group flex flex-1 flex-col items-center justify-center gap-1 rounded-xl px-2 py-2 text-[0.75rem] font-semibold uppercase tracking-wide transition-all duration-200 ease-out md:text-xs",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2 focus-visible:ring-offset-nav",
                  "min-h-[56px]",
                  isActive ? "text-primary" : "text-muted-foreground",
                )
              }
              aria-label={`${tab.label} tab`}
            >
              {({ isActive }) => (
                <>
                  <Icon
                    name={tab.icon}
                    sizeRem={1.35}
                    aria-hidden
                    className={cn(
                      "transition-all duration-200 ease-out",
                      isActive ? "text-primary" : "text-muted-foreground",
                    )}
                  />
                  <span className="leading-none font-gilroy">{tab.label}</span>
                </>
              )}
            </NavLink>
          ))}
        </nav>
      </div>
    );
  },
);

