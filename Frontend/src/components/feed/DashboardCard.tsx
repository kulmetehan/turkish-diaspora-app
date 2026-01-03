// Frontend/src/components/feed/DashboardCard.tsx
import { Icon } from "@/components/Icon";
import { cn } from "@/lib/ui/cn";
import { useNavigate } from "react-router-dom";

export interface DashboardCardProps {
  title: string;
  icon: React.ComponentProps<typeof Icon>["name"];
  children: React.ReactNode;
  footerLink?: string;
  footerText?: string;
  className?: string;
  backgroundImage?: string;
  backgroundOpacity?: number;
}

export function DashboardCard({
  title,
  icon,
  children,
  footerLink,
  footerText,
  className,
  backgroundImage,
  backgroundOpacity = 0.2,
}: DashboardCardProps) {
  const navigate = useNavigate();

  const handleFooterClick = () => {
    if (footerLink) {
      // Support hash routes (e.g., #/news?feed=trending&trend_country=nl)
      if (footerLink.startsWith("#")) {
        const hashPath = footerLink.slice(1); // Remove leading #
        window.location.hash = hashPath;
      } else {
        navigate(footerLink);
      }
    }
  };

  return (
    <div
      className={cn(
        "relative flex flex-col rounded-xl border border-border/50 bg-card p-4 shadow-soft transition-shadow hover:shadow-md",
        "min-h-[160px]",
        backgroundImage && "overflow-hidden",
        className
      )}
    >
      {/* Background Image Overlay */}
      {backgroundImage && (
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            backgroundImage: `url(${backgroundImage})`,
            backgroundSize: "contain",
            backgroundPosition: "center",
            backgroundRepeat: "no-repeat",
            opacity: backgroundOpacity,
          }}
        />
      )}

      {/* Content Layer - positioned above background */}
      <div className="relative z-10 flex flex-col flex-1">
        {/* Header */}
        <div className="mb-3 flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Icon name={icon} sizeRem={1.2} />
          </div>
          <h3 className="text-xs font-gilroy font-semibold text-foreground">{title}</h3>
        </div>

        {/* Content */}
        <div className="flex-1 text-sm font-gilroy font-normal text-muted-foreground">{children}</div>

        {/* Footer */}
        {footerLink && footerText && (
          <button
            onClick={handleFooterClick}
            className="mt-3 text-left text-sm font-gilroy font-medium text-primary transition-colors hover:text-primary/80"
          >
            {footerText} →
          </button>
        )}
      </div>
    </div>
  );
}








