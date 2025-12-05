// Frontend/src/pages/DiasporaPulsePage.tsx
import { useState, useEffect, useMemo } from "react";
import { AppViewportShell, PageShell } from "@/components/layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DiasporaPulseLite } from "@/components/trending/DiasporaPulseLite";
import { 
  getCityStats, 
  getTrendingLocations, 
  type CityStats, 
  type TrendingLocation 
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
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
} from "recharts";
import { Icon } from "@/components/Icon";
import { cn } from "@/lib/ui/cn";

const AVAILABLE_CITIES = [
  { key: "rotterdam", label: "Rotterdam" },
  { key: "den_haag", label: "Den Haag" },
  { key: "amsterdam", label: "Amsterdam" },
  { key: "utrecht", label: "Utrecht" },
];

const COLORS = ["#DC2626", "#EF4444", "#F87171", "#FCA5A5", "#FECACA"];

export default function DiasporaPulsePage() {
  const [selectedCity, setSelectedCity] = useState<string>("all");
  const [windowDays, setWindowDays] = useState<number>(7);
  const [cityStats, setCityStats] = useState<CityStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"overview" | "trending" | "cities">("overview");

  useEffect(() => {
    loadAllStats();
  }, [windowDays]);

  const loadAllStats = async () => {
    setLoading(true);
    try {
      const statsPromises = AVAILABLE_CITIES.map((city) =>
        getCityStats(city.key, windowDays).catch((err) => {
          console.warn(`Failed to load stats for ${city.key}:`, err);
          return null;
        })
      );
      const results = await Promise.all(statsPromises);
      setCityStats(results.filter((stat): stat is CityStats => stat !== null));
    } catch (err) {
      toast.error("Failed to load statistics", {
        description: err instanceof Error ? err.message : "Unknown error",
      });
    } finally {
      setLoading(false);
    }
  };

  const chartData = useMemo(() => {
    return cityStats.map((stat) => ({
      name: AVAILABLE_CITIES.find((c) => c.key === stat.city_key)?.label || stat.city_key,
      "Check-ins": stat.check_ins_count,
      "Reactions": stat.reactions_count,
      "Notes": stat.notes_count,
      "Favorites": stat.favorites_count,
      "Total": stat.total_activity,
    }));
  }, [cityStats]);

  const activityBreakdown = useMemo(() => {
    if (cityStats.length === 0) return [];
    
    const total = cityStats.reduce((acc, stat) => ({
      check_ins: acc.check_ins + stat.check_ins_count,
      reactions: acc.reactions + stat.reactions_count,
      notes: acc.notes + stat.notes_count,
      favorites: acc.favorites + stat.favorites_count,
      poll_responses: acc.poll_responses + stat.poll_responses_count,
    }), { check_ins: 0, reactions: 0, notes: 0, favorites: 0, poll_responses: 0 });

    const totalActivity = total.check_ins + total.reactions + total.notes + total.favorites + total.poll_responses;
    
    return [
      { name: "Check-ins", value: total.check_ins, percentage: totalActivity > 0 ? (total.check_ins / totalActivity) * 100 : 0 },
      { name: "Reactions", value: total.reactions, percentage: totalActivity > 0 ? (total.reactions / totalActivity) * 100 : 0 },
      { name: "Notes", value: total.notes, percentage: totalActivity > 0 ? (total.notes / totalActivity) * 100 : 0 },
      { name: "Favorites", value: total.favorites, percentage: totalActivity > 0 ? (total.favorites / totalActivity) * 100 : 0 },
      { name: "Poll Responses", value: total.poll_responses, percentage: totalActivity > 0 ? (total.poll_responses / totalActivity) * 100 : 0 },
    ];
  }, [cityStats]);

  const selectedCityStats = useMemo(() => {
    if (!selectedCity || selectedCity === "all") return null;
    return cityStats.find((stat) => stat.city_key === selectedCity);
  }, [cityStats, selectedCity]);

  return (
    <AppViewportShell variant="content">
      <PageShell
        title="Diaspora Pulse"
        subtitle="Analytics dashboard voor de Turkish diaspora community"
        maxWidth="full"
      >
        <div className="space-y-6">
          {/* Time Window Selector */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Select
                value={windowDays.toString()}
                onValueChange={(value) => setWindowDays(Number(value))}
              >
                <SelectTrigger className="w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">Laatste dag</SelectItem>
                  <SelectItem value="7">Laatste week</SelectItem>
                  <SelectItem value="30">Laatste maand</SelectItem>
                  <SelectItem value="90">Laatste 3 maanden</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as typeof activeTab)} className="w-full">
            <TabsList className="grid w-full grid-cols-3 mb-6">
              <TabsTrigger value="overview">Overzicht</TabsTrigger>
              <TabsTrigger value="cities">Steden</TabsTrigger>
              <TabsTrigger value="trending">Trending</TabsTrigger>
            </TabsList>

            {/* Overview Tab */}
            <TabsContent value="overview" className="space-y-6">
              {loading ? (
                <div className="grid gap-6 md:grid-cols-2">
                  <Skeleton className="h-64 w-full" />
                  <Skeleton className="h-64 w-full" />
                </div>
              ) : (
                <>
                  {/* Activity Breakdown Pie Chart */}
                  <Card>
                    <CardHeader>
                      <CardTitle>Activiteit Verdeling</CardTitle>
                    </CardHeader>
                    <CardContent>
                      {activityBreakdown.length > 0 ? (
                        <div className="grid gap-6 md:grid-cols-2">
                          <ResponsiveContainer width="100%" height={300}>
                            <PieChart>
                              <Pie
                                data={activityBreakdown}
                                cx="50%"
                                cy="50%"
                                labelLine={false}
                                label={({ name, percentage }) => `${name}: ${percentage.toFixed(1)}%`}
                                outerRadius={100}
                                fill="#8884d8"
                                dataKey="value"
                              >
                                {activityBreakdown.map((entry, index) => (
                                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                ))}
                              </Pie>
                              <Tooltip />
                            </PieChart>
                          </ResponsiveContainer>
                          <div className="flex flex-col justify-center space-y-2">
                            {activityBreakdown.map((item, index) => (
                              <div key={item.name} className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                  <div
                                    className="w-4 h-4 rounded"
                                    style={{ backgroundColor: COLORS[index % COLORS.length] }}
                                  />
                                  <span className="text-sm font-medium">{item.name}</span>
                                </div>
                                <div className="text-right">
                                  <span className="text-sm font-semibold">{item.value.toLocaleString()}</span>
                                  <span className="text-xs text-muted-foreground ml-2">
                                    ({item.percentage.toFixed(1)}%)
                                  </span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ) : (
                        <div className="text-center text-muted-foreground py-8">
                          Geen activiteit in deze periode
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  {/* City Comparison Bar Chart */}
                  <Card>
                    <CardHeader>
                      <CardTitle>Vergelijking per Stad</CardTitle>
                    </CardHeader>
                    <CardContent>
                      {chartData.length > 0 ? (
                        <ResponsiveContainer width="100%" height={400}>
                          <BarChart data={chartData}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="name" />
                            <YAxis />
                            <Tooltip />
                            <Legend />
                            <Bar dataKey="Check-ins" fill="#DC2626" />
                            <Bar dataKey="Reactions" fill="#EF4444" />
                            <Bar dataKey="Notes" fill="#F87171" />
                            <Bar dataKey="Favorites" fill="#FCA5A5" />
                          </BarChart>
                        </ResponsiveContainer>
                      ) : (
                        <div className="text-center text-muted-foreground py-8">
                          Geen data beschikbaar
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </>
              )}
            </TabsContent>

            {/* Cities Tab */}
            <TabsContent value="cities" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Stad Selectie</CardTitle>
                </CardHeader>
                <CardContent>
                  <Select value={selectedCity} onValueChange={setSelectedCity}>
                    <SelectTrigger className="w-full md:w-64">
                      <SelectValue placeholder="Selecteer een stad" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Alle steden</SelectItem>
                      {AVAILABLE_CITIES.map((city) => (
                        <SelectItem key={city.key} value={city.key}>
                          {city.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </CardContent>
              </Card>

              {selectedCity && selectedCity !== "all" && selectedCityStats ? (
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Check-ins</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-3xl font-bold">{selectedCityStats.check_ins_count.toLocaleString()}</div>
                      <p className="text-sm text-muted-foreground mt-1">
                        in de laatste {windowDays} dagen
                      </p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Reacties</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-3xl font-bold">{selectedCityStats.reactions_count.toLocaleString()}</div>
                      <p className="text-sm text-muted-foreground mt-1">
                        in de laatste {windowDays} dagen
                      </p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Notities</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-3xl font-bold">{selectedCityStats.notes_count.toLocaleString()}</div>
                      <p className="text-sm text-muted-foreground mt-1">
                        in de laatste {windowDays} dagen
                      </p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Favorieten</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-3xl font-bold">{selectedCityStats.favorites_count.toLocaleString()}</div>
                      <p className="text-sm text-muted-foreground mt-1">
                        in de laatste {windowDays} dagen
                      </p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Trending Locaties</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-3xl font-bold">
                        {selectedCityStats.trending_locations_count.toLocaleString()}
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">Huidige trending</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Unieke Locaties</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-3xl font-bold">
                        {selectedCityStats.unique_locations_count.toLocaleString()}
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">
                        met activiteit in deze periode
                      </p>
                    </CardContent>
                  </Card>
                </div>
              ) : selectedCity && selectedCity !== "all" ? (
                <Card>
                  <CardContent className="py-8 text-center text-muted-foreground">
                    Geen statistieken beschikbaar voor deze stad
                  </CardContent>
                </Card>
              ) : (
                <Card>
                  <CardContent className="py-8 text-center text-muted-foreground">
                    Selecteer een stad om statistieken te bekijken
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            {/* Trending Tab */}
            <TabsContent value="trending" className="mt-0">
              <DiasporaPulseLite />
            </TabsContent>
          </Tabs>
        </div>
      </PageShell>
    </AppViewportShell>
  );
}

