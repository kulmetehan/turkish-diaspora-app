import { useLocation, Link } from "react-router-dom";
import { Icon } from "@/components/Icon";
import { cn } from "@/lib/ui/cn";
import { generateBreadcrumbs } from "@/lib/admin/breadcrumbs";

export default function AdminBreadcrumbs() {
  const location = useLocation();
  const breadcrumbs = generateBreadcrumbs(location.pathname);
  
  if (breadcrumbs.length <= 1) {
    return null;
  }
  
  return (
    <nav aria-label="Breadcrumb" className="flex items-center space-x-2 text-sm overflow-x-auto md:overflow-x-visible">
      <ol className="flex items-center space-x-2 min-w-max">
        {breadcrumbs.map((segment, index) => {
          const isLast = index === breadcrumbs.length - 1;
          
          return (
            <li key={segment.path} className="flex items-center">
              {index > 0 && (
                <Icon 
                  name="ChevronRight" 
                  sizeRem={1} 
                  className="mx-2 text-muted-foreground"
                  aria-hidden="true"
                />
              )}
              {isLast ? (
                <span 
                  className="font-medium text-foreground"
                  aria-current="page"
                >
                  {segment.label}
                </span>
              ) : (
                <Link
                  to={segment.path}
                  className={cn(
                    "text-muted-foreground hover:text-foreground transition-colors",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded"
                  )}
                >
                  {segment.label}
                </Link>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

