import { Link } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/Icon";
import { adminNavigation } from "@/lib/admin/navigation";

export default function DashboardPage() {
  // Get main navigation items for quick links
  const mainItems = adminNavigation
    .flatMap((group) => group.items)
    .filter((item) => item.path !== "/admin") // Exclude self
    .slice(0, 8); // Top 8 items

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Admin Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Overview and quick access to all admin sections
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {mainItems.map((item) => (
          <Card key={item.id} className="rounded-2xl shadow-sm hover:shadow-md transition-shadow">
            <CardHeader>
              <div className="flex items-center gap-3">
                <Icon name={item.icon} sizeRem={1.5} className="text-primary" />
                <CardTitle className="text-lg">{item.label}</CardTitle>
              </div>
              {item.badge && (
                <CardDescription className="mt-1">
                  <span className="text-xs bg-muted px-2 py-1 rounded">{item.badge}</span>
                </CardDescription>
              )}
            </CardHeader>
            <CardContent>
              <Link to={item.path}>
                <Button variant="outline" className="w-full">
                  Open {item.label}
                </Button>
              </Link>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="rounded-2xl shadow-sm">
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>
            Common administrative tasks and shortcuts
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            <Link to="/admin/locations">
              <Button variant="outline" className="w-full justify-start">
                <Icon name="MapPin" sizeRem={1.25} className="mr-2" />
                View Locations
              </Button>
            </Link>
            <Link to="/admin/workers">
              <Button variant="outline" className="w-full justify-start">
                <Icon name="Cog" sizeRem={1.25} className="mr-2" />
                Manage Workers
              </Button>
            </Link>
            <Link to="/admin/metrics">
              <Button variant="outline" className="w-full justify-start">
                <Icon name="BarChart3" sizeRem={1.25} className="mr-2" />
                View Metrics
              </Button>
            </Link>
            <Link to="/admin/cities">
              <Button variant="outline" className="w-full justify-start">
                <Icon name="Building2" sizeRem={1.25} className="mr-2" />
                Manage Cities
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}























