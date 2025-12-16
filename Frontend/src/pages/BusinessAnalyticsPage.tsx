// Frontend/src/pages/BusinessAnalyticsPage.tsx
import { useState, useEffect } from "react";
import { AppViewportShell, PageShell } from "@/components/layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { 
  getBusinessAnalyticsOverview, 
  getEngagementMetrics,
  getTrendingMetrics,
  type BusinessAnalyticsOverview as OverviewType,
  type EngagementMetrics,
  type TrendingMetrics,
} from "@/lib/api";
import { toast } from "sonner";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
} from "recharts";

export default function BusinessAnalyticsPage() {
  const [periodDays, setPeriodDays] = useState<number>(7);
  const [overview, setOverview] = useState<OverviewType | null>(null);
  const [engagement, setEngagement] = useState<EngagementMetrics | null>(null);
  const [trending, setTrending] = useState<TrendingMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAnalytics();
  }, [periodDays]);

  const loadAnalytics = async () => {
    setLoading(true);
    try {
      const [overviewData, engagementData, trendingData] = await Promise.all([
        getBusinessAnalyticsOverview(periodDays),
        getEngagementMetrics(periodDays),
        getTrendingMetrics(),
      ]);
      
      setOverview(overviewData);
      setEngagement(engagementData);
      setTrending(trendingData);
    } catch (err) {
      toast.error("Failed to load analytics", {
        description: err instanceof Error ? err.message : "Unknown error",
      });
    } finally {
      setLoading(false);
    }
  };

  const timelineData = engagement?.activity_timeline.map(item => ({
    date: new Date(item.date).toLocaleDateString(),
    count: item.count,
  })) || [];

  return (
    <AppViewportShell variant="content">
      <PageShell
        title="Business Analytics"
        subtitle="Insights into your claimed locations' performance"
        maxWidth="full"
      >
        <div className="space-y-6">
          {/* Time Period Selector */}
          <div className="flex items-center justify-between">
            <Select
              value={periodDays.toString()}
              onValueChange={(value) => setPeriodDays(Number(value))}
            >
              <SelectTrigger className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1">Last day</SelectItem>
                <SelectItem value="7">Last week</SelectItem>
                <SelectItem value="30">Last month</SelectItem>
                <SelectItem value="90">Last 3 months</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {loading ? (
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
              <Skeleton className="h-32 w-full" />
              <Skeleton className="h-32 w-full" />
              <Skeleton className="h-32 w-full" />
              <Skeleton className="h-32 w-full" />
            </div>
          ) : overview ? (
            <>
              {/* Overview Cards */}
              <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Total Locations</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold">{overview.total_locations}</div>
                    <p className="text-sm text-muted-foreground mt-1">
                      {overview.approved_locations} approved
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Total Engagement</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold">
                      {overview.total_check_ins + overview.total_reactions + overview.total_notes + overview.total_favorites}
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">
                      Check-ins, reactions, notes, favorites
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Trending Locations</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold">{overview.trending_locations}</div>
                    <p className="text-sm text-muted-foreground mt-1">
                      Currently trending
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Check-ins</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold">{overview.total_check_ins}</div>
                    <p className="text-sm text-muted-foreground mt-1">
                      In the last {periodDays} days
                    </p>
                  </CardContent>
                </Card>
              </div>

              {/* Engagement Breakdown */}
              {engagement && (
                <Card>
                  <CardHeader>
                    <CardTitle>Engagement Breakdown</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-4 md:grid-cols-2">
                      <div>
                        <h3 className="text-sm font-medium mb-2">Top Locations</h3>
                        <div className="space-y-2">
                          {engagement.top_locations.slice(0, 5).map((loc) => (
                            <div key={loc.location_id} className="flex justify-between text-sm">
                              <span>Location #{loc.location_id}</span>
                              <span className="font-medium">{loc.engagement_count}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                      <div>
                        <h3 className="text-sm font-medium mb-2">Activity Timeline</h3>
                        {timelineData.length > 0 ? (
                          <ResponsiveContainer width="100%" height={200}>
                            <LineChart data={timelineData}>
                              <CartesianGrid strokeDasharray="3 3" />
                              <XAxis dataKey="date" />
                              <YAxis />
                              <Tooltip />
                              <Line type="monotone" dataKey="count" stroke="#DC2626" />
                            </LineChart>
                          </ResponsiveContainer>
                        ) : (
                          <p className="text-sm text-muted-foreground">No activity data</p>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Trending Locations */}
              {trending && trending.trending_locations.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Trending Locations</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {trending.trending_locations.slice(0, 10).map((loc) => (
                        <div key={loc.location_id} className="flex justify-between items-center p-2 border rounded">
                          <span>Location #{loc.location_id}</span>
                          <span className="font-medium">Score: {loc.trending_score.toFixed(2)}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </>
          ) : (
            <Card>
              <CardContent className="py-8 text-center text-muted-foreground">
                No analytics data available
              </CardContent>
            </Card>
          )}
        </div>
      </PageShell>
    </AppViewportShell>
  );
}

















