import { cn } from "@/lib/ui/cn";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/Icon";
import AdminBreadcrumbs from "./AdminBreadcrumbs";
import AdminUserMenu from "./AdminUserMenu";

interface AdminHeaderProps {
  onMobileMenuClick?: () => void;
}

export default function AdminHeader({ onMobileMenuClick }: AdminHeaderProps) {
  return (
    <header
      className={cn(
        "sticky top-0 z-30 flex h-16 items-center justify-between border-b bg-background px-4 md:px-6",
        "backdrop-blur supports-[backdrop-filter]:bg-background/95"
      )}
    >
      <div className="flex items-center gap-4">
        {onMobileMenuClick && (
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={onMobileMenuClick}
            aria-label="Open navigation menu"
          >
            <Icon name="Menu" sizeRem={1.25} />
          </Button>
        )}
        <AdminBreadcrumbs />
      </div>
      <AdminUserMenu />
    </header>
  );
}

