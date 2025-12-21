// Frontend/src/pages/BusinessPromotionsPage.tsx
import { useState, useEffect } from "react";
import { AppViewportShell, PageShell } from "@/components/layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import {
  listLocationPromotions,
  listNewsPromotions,
  cancelLocationPromotion,
  cancelNewsPromotion,
  type LocationPromotion,
  type NewsPromotion,
} from "@/lib/api/promotions";
import { toast } from "sonner";
import PromoteLocationForm from "@/components/promotions/PromoteLocationForm";
import PromoteNewsForm from "@/components/promotions/PromoteNewsForm";

export default function BusinessPromotionsPage() {
  const [locationPromotions, setLocationPromotions] = useState<LocationPromotion[]>([]);
  const [newsPromotions, setNewsPromotions] = useState<NewsPromotion[]>([]);
  const [loading, setLoading] = useState(true);
  const [showLocationForm, setShowLocationForm] = useState(false);
  const [showNewsForm, setShowNewsForm] = useState(false);

  useEffect(() => {
    loadPromotions();
  }, []);

  const loadPromotions = async () => {
    setLoading(true);
    try {
      const [locations, news] = await Promise.all([
        listLocationPromotions(),
        listNewsPromotions(),
      ]);
      setLocationPromotions(locations);
      setNewsPromotions(news);
    } catch (err) {
      toast.error("Failed to load promotions", {
        description: err instanceof Error ? err.message : "Unknown error",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCancelLocation = async (id: number) => {
    try {
      await cancelLocationPromotion(id);
      toast.success("Promotion cancelled");
      loadPromotions();
    } catch (err) {
      toast.error("Failed to cancel promotion", {
        description: err instanceof Error ? err.message : "Unknown error",
      });
    }
  };

  const handleCancelNews = async (id: number) => {
    try {
      await cancelNewsPromotion(id);
      toast.success("Promotion cancelled");
      loadPromotions();
    } catch (err) {
      toast.error("Failed to cancel promotion", {
        description: err instanceof Error ? err.message : "Unknown error",
      });
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "active":
        return "text-green-600";
      case "pending":
        return "text-yellow-600";
      case "expired":
        return "text-gray-600";
      case "cancelled":
        return "text-red-600";
      default:
        return "text-gray-600";
    }
  };

  return (
    <AppViewportShell variant="content">
      <PageShell
        title="Promotions"
        subtitle="Manage your location and news promotions"
        maxWidth="full"
      >
        <div className="space-y-6">
          {/* Action Buttons */}
          <div className="flex gap-4">
            <Button onClick={() => setShowLocationForm(true)}>
              Promote Location
            </Button>
            <Button onClick={() => setShowNewsForm(true)} variant="outline">
              Promote News
            </Button>
          </div>

          {/* Forms */}
          {showLocationForm && (
            <PromoteLocationForm
              onSuccess={() => {
                setShowLocationForm(false);
                loadPromotions();
              }}
              onCancel={() => setShowLocationForm(false)}
            />
          )}

          {showNewsForm && (
            <PromoteNewsForm
              onSuccess={() => {
                setShowNewsForm(false);
                loadPromotions();
              }}
              onCancel={() => setShowNewsForm(false)}
            />
          )}

          {/* Promotions List */}
          <Tabs defaultValue="locations" className="w-full">
            <TabsList>
              <TabsTrigger value="locations">Location Promotions</TabsTrigger>
              <TabsTrigger value="news">News Promotions</TabsTrigger>
            </TabsList>

            <TabsContent value="locations" className="space-y-4">
              {loading ? (
                <Skeleton className="h-32 w-full" />
              ) : locationPromotions.length === 0 ? (
                <Card>
                  <CardContent className="py-8 text-center text-muted-foreground">
                    No location promotions yet. Create one to get started.
                  </CardContent>
                </Card>
              ) : (
                locationPromotions.map((promo) => (
                  <Card key={promo.id}>
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <CardTitle>{promo.location_name || `Location #${promo.location_id}`}</CardTitle>
                        <span className={`text-sm font-medium ${getStatusColor(promo.status)}`}>
                          {promo.status}
                        </span>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        <p className="text-sm">
                          <span className="font-medium">Type:</span> {promo.promotion_type}
                        </p>
                        <p className="text-sm">
                          <span className="font-medium">Starts:</span>{" "}
                          {new Date(promo.starts_at).toLocaleDateString()}
                        </p>
                        <p className="text-sm">
                          <span className="font-medium">Ends:</span>{" "}
                          {new Date(promo.ends_at).toLocaleDateString()}
                        </p>
                        {(promo.status === "pending" || promo.status === "active") && (
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => handleCancelLocation(promo.id)}
                            className="mt-2"
                          >
                            Cancel
                          </Button>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </TabsContent>

            <TabsContent value="news" className="space-y-4">
              {loading ? (
                <Skeleton className="h-32 w-full" />
              ) : newsPromotions.length === 0 ? (
                <Card>
                  <CardContent className="py-8 text-center text-muted-foreground">
                    No news promotions yet. Create one to get started.
                  </CardContent>
                </Card>
              ) : (
                newsPromotions.map((promo) => (
                  <Card key={promo.id}>
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <CardTitle>{promo.title}</CardTitle>
                        <span className={`text-sm font-medium ${getStatusColor(promo.status)}`}>
                          {promo.status}
                        </span>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        <p className="text-sm line-clamp-2">{promo.content}</p>
                        <p className="text-sm">
                          <span className="font-medium">Starts:</span>{" "}
                          {new Date(promo.starts_at).toLocaleDateString()}
                        </p>
                        <p className="text-sm">
                          <span className="font-medium">Ends:</span>{" "}
                          {new Date(promo.ends_at).toLocaleDateString()}
                        </p>
                        {(promo.status === "pending" || promo.status === "active") && (
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => handleCancelNews(promo.id)}
                            className="mt-2"
                          >
                            Cancel
                          </Button>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </TabsContent>
          </Tabs>
        </div>
      </PageShell>
    </AppViewportShell>
  );
}























