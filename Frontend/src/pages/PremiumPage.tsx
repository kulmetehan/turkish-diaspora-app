// Frontend/src/pages/PremiumPage.tsx
import { useState, useEffect } from "react";
import { AppViewportShell, PageShell } from "@/components/layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { 
  getSubscriptionStatus, 
  getFeatures,
  createSubscription,
  type SubscriptionStatus,
  type FeaturesResponse,
} from "@/lib/api";
import { toast } from "sonner";

const TIERS = [
  {
    name: "Basic",
    price: "Free",
    features: ["Standard location claiming", "Basic analytics", "Standard location display"],
  },
  {
    name: "Premium",
    price: "€29/month",
    features: [
      "Enhanced location information",
      "Advanced analytics dashboard",
      "Priority support",
      "Premium location badges",
      "Extended analytics history (90 days)",
    ],
  },
  {
    name: "Pro",
    price: "€99/month",
    features: [
      "All Premium features",
      "API access",
      "Custom branding",
      "Dedicated account manager",
      "Unlimited analytics history",
    ],
  },
];

export default function PremiumPage() {
  const [subscription, setSubscription] = useState<SubscriptionStatus | null>(null);
  const [features, setFeatures] = useState<FeaturesResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSubscription();
  }, []);

  const loadSubscription = async () => {
    setLoading(true);
    try {
      const [subData, featuresData] = await Promise.all([
        getSubscriptionStatus(),
        getFeatures(),
      ]);
      setSubscription(subData);
      setFeatures(featuresData);
    } catch (err) {
      toast.error("Failed to load subscription", {
        description: err instanceof Error ? err.message : "Unknown error",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSubscribe = async (tier: "premium" | "pro") => {
    try {
      const result = await createSubscription({
        tier,
        success_url: `${window.location.origin}/premium?success=true`,
        cancel_url: `${window.location.origin}/premium?canceled=true`,
      });
      
      // Redirect to Stripe Checkout
      window.location.href = result.url;
    } catch (err) {
      toast.error("Failed to create subscription", {
        description: err instanceof Error ? err.message : "Unknown error",
      });
    }
  };

  return (
    <AppViewportShell variant="content">
      <PageShell
        title="Premium Features"
        subtitle="Upgrade your business account for enhanced features"
        maxWidth="full"
      >
        <div className="space-y-6">
          {/* Current Subscription Status */}
          {loading ? (
            <Skeleton className="h-32 w-full" />
          ) : subscription ? (
            <Card>
              <CardHeader>
                <CardTitle>Current Subscription</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-lg font-semibold capitalize">{subscription.tier}</p>
                    <p className="text-sm text-muted-foreground">
                      Status: {subscription.status}
                    </p>
                    {subscription.current_period_end && (
                      <p className="text-sm text-muted-foreground">
                        Renews: {new Date(subscription.current_period_end).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                  <div>
                    <p className="text-sm font-medium">Enabled Features:</p>
                    <ul className="text-sm text-muted-foreground mt-1">
                      {subscription.enabled_features.map((feature) => (
                        <li key={feature}>• {feature.replace(/_/g, " ")}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </CardContent>
            </Card>
          ) : null}

          {/* Subscription Tiers */}
          <div className="grid gap-6 md:grid-cols-3">
            {TIERS.map((tier) => (
              <Card key={tier.name} className={subscription?.tier === tier.name.toLowerCase() ? "border-primary" : ""}>
                <CardHeader>
                  <CardTitle>{tier.name}</CardTitle>
                  <p className="text-2xl font-bold mt-2">{tier.price}</p>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2 mb-4">
                    {tier.features.map((feature, idx) => (
                      <li key={idx} className="text-sm">• {feature}</li>
                    ))}
                  </ul>
                  {tier.name !== "Basic" && (
                    <Button
                      onClick={() => handleSubscribe(tier.name.toLowerCase() as "premium" | "pro")}
                      className="w-full"
                      variant={subscription?.tier === tier.name.toLowerCase() ? "outline" : "default"}
                      disabled={subscription?.tier === tier.name.toLowerCase()}
                    >
                      {subscription?.tier === tier.name.toLowerCase() ? "Current Plan" : "Subscribe"}
                    </Button>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </PageShell>
    </AppViewportShell>
  );
}













