import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { 
  getOutreachMetrics, 
  getDailyOutreachMetrics, 
  getCampaignDays,
  type OutreachMetricsResponse,
  type DailyOutreachMetrics,
} from "@/lib/apiAdmin";
import { toast } from "sonner";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { cn } from "@/lib/ui/cn";
import { TrendingUp, Mail, CheckCircle, XCircle, MousePointerClick } from "lucide-react";

export default function AdminOutreachMetricsPage() {
  const [overview, setOverview] = useState<OutreachMetricsResponse | null>(null);
  const [dailyMetrics, setDailyMetrics] = useState<DailyOutreachMetrics[]>([]);
  const [campaignDays, setCampaignDays] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadMetrics();
  }, []);

  const loadMetrics = async () => {
    setLoading(true);
    try {
      const [overviewData, campaignDaysData] = await Promise.all([
        getOutreachMetrics(),
        getCampaignDays(),
      ]);
      
      setOverview(overviewData);
      setCampaignDays(campaignDaysData);
      
      // Load daily metrics for all campaign days
      if (campaignDaysData.length > 0) {
        const dailyData = await Promise.all(
          campaignDaysData.map(day => getDailyOutreachMetrics(day))
        );
        setDailyMetrics(dailyData);
      }
    } catch (err) {
      toast.error("Failed to load outreach metrics", {
        description: err instanceof Error ? err.message : "Unknown error",
      });
    } finally {
      setLoading(false);
    }
  };

  const getKPIStatus = (rate: number, threshold: { min?: number; max?: number }) => {
    if (threshold.max !== undefined && rate > threshold.max) {
      return "critical";
    }
    if (threshold.min !== undefined && rate < threshold.min) {
      return "warning";
    }
    return "ok";
  };

  const getStatusBadge = (status: "ok" | "warning" | "critical") => {
    const variants = {
      ok: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
      warning: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
      critical: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
    };
    return variants[status];
  };

  const chartData = dailyMetrics.map(day => ({
    day: `Day ${day.campaign_day}`,
    campaign_day: day.campaign_day,
    emails_sent: day.emails_sent,
    emails_delivered: day.emails_delivered,
    emails_clicked: day.emails_clicked,
    delivery_rate: day.delivery_rate,
    click_rate: day.click_rate,
    bounce_rate: day.bounce_rate,
    claim_rate: day.claim_rate,
  }));

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Outreach Metrics</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Monitor outreach email campaign performance and KPIs
        </p>
      </div>

      {/* Overview Cards */}
      {loading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map(i => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-4 w-24" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-16" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : overview ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Emails Sent</CardTitle>
              <Mail className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{overview.mails_sent}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Delivery Rate</CardTitle>
              <CheckCircle className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {overview.mails_sent > 0 
                  ? `${((overview.mails_sent - (overview.mails_sent * overview.bounce_rate / 100)) / overview.mails_sent * 100).toFixed(1)}%`
                  : "0%"}
              </div>
              <Badge 
                className={cn(
                  "mt-2",
                  getStatusBadge(getKPIStatus(
                    overview.mails_sent > 0 
                      ? ((overview.mails_sent - (overview.mails_sent * overview.bounce_rate / 100)) / overview.mails_sent * 100)
                      : 0,
                    { min: 90 }
                  ))
                )}
              >
                {getKPIStatus(
                  overview.mails_sent > 0 
                    ? ((overview.mails_sent - (overview.mails_sent * overview.bounce_rate / 100)) / overview.mails_sent * 100)
                    : 0,
                  { min: 90 }
                ) === "critical" ? "Critical" : getKPIStatus(
                  overview.mails_sent > 0 
                    ? ((overview.mails_sent - (overview.mails_sent * overview.bounce_rate / 100)) / overview.mails_sent * 100)
                    : 0,
                  { min: 90 }
                ) === "warning" ? "Warning" : "OK"}
              </Badge>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Click Rate</CardTitle>
              <MousePointerClick className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{overview.click_rate.toFixed(1)}%</div>
              <Badge 
                className={cn(
                  "mt-2",
                  getStatusBadge(getKPIStatus(overview.click_rate, { min: 10 }))
                )}
              >
                {getKPIStatus(overview.click_rate, { min: 10 }) === "critical" ? "Critical" : getKPIStatus(overview.click_rate, { min: 10 }) === "warning" ? "Warning" : "OK"}
              </Badge>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Claim Rate</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{overview.claim_rate.toFixed(1)}%</div>
            </CardContent>
          </Card>
        </div>
      ) : null}

      {/* Campaign Days Table */}
      {loading ? (
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-48" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-64 w-full" />
          </CardContent>
        </Card>
      ) : dailyMetrics.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Campaign Day Metrics</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-2">Day</th>
                    <th className="text-right p-2">Sent</th>
                    <th className="text-right p-2">Delivered</th>
                    <th className="text-right p-2">Clicked</th>
                    <th className="text-right p-2">Bounced</th>
                    <th className="text-right p-2">Delivery Rate</th>
                    <th className="text-right p-2">Click Rate</th>
                    <th className="text-right p-2">Bounce Rate</th>
                    <th className="text-right p-2">Claim Rate</th>
                    <th className="text-center p-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {dailyMetrics.map(day => {
                    const deliveryStatus = getKPIStatus(day.delivery_rate, { min: 90 });
                    const bounceStatus = getKPIStatus(day.bounce_rate, { max: 5 });
                    const clickStatus = getKPIStatus(day.click_rate, { min: 10 });
                    const overallStatus = deliveryStatus === "critical" || bounceStatus === "critical" 
                      ? "critical" 
                      : deliveryStatus === "warning" || bounceStatus === "warning" || clickStatus === "warning"
                      ? "warning"
                      : "ok";
                    
                    return (
                      <tr key={day.campaign_day} className="border-b hover:bg-muted/50">
                        <td className="p-2 font-medium">Day {day.campaign_day}</td>
                        <td className="text-right p-2">{day.emails_sent}</td>
                        <td className="text-right p-2">{day.emails_delivered}</td>
                        <td className="text-right p-2">{day.emails_clicked}</td>
                        <td className="text-right p-2">{day.emails_bounced}</td>
                        <td className="text-right p-2">{day.delivery_rate.toFixed(1)}%</td>
                        <td className="text-right p-2">{day.click_rate.toFixed(1)}%</td>
                        <td className="text-right p-2">{day.bounce_rate.toFixed(1)}%</td>
                        <td className="text-right p-2">{day.claim_rate.toFixed(1)}%</td>
                        <td className="text-center p-2">
                          <Badge className={getStatusBadge(overallStatus)}>
                            {overallStatus === "critical" ? "Critical" : overallStatus === "warning" ? "Warning" : "OK"}
                          </Badge>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Campaign Day Metrics</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">No campaign days found. Start a campaign to see metrics here.</p>
          </CardContent>
        </Card>
      )}

      {/* Trend Chart */}
      {loading ? (
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-48" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-64 w-full" />
          </CardContent>
        </Card>
      ) : chartData.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Campaign Trends</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="day" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="emails_sent" stroke="#8884d8" name="Emails Sent" />
                <Line type="monotone" dataKey="emails_delivered" stroke="#82ca9d" name="Delivered" />
                <Line type="monotone" dataKey="emails_clicked" stroke="#ffc658" name="Clicked" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}

