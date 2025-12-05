import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { AppViewportShell, PageShell } from "@/components/layout";
import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import { getTheme, setTheme, type ThemeSetting } from "@/lib/theme/darkMode";
import { PrivacySettings } from "@/components/settings/PrivacySettings";
import { ActivityHistory } from "@/components/activity/ActivityHistory";
import { ReferralShare } from "@/components/referrals/ReferralShare";
import { useUserAuth } from "@/hooks/useUserAuth";
import { supabase } from "@/lib/supabaseClient";
import { toast } from "sonner";

export default function AccountPage() {
  const [theme, setThemeState] = useState<ThemeSetting>("system");
  const { isAuthenticated, userId, email, isLoading } = useUserAuth();
  const navigate = useNavigate();

  useEffect(() => {
    setThemeState(getTheme());
  }, []);

  const handleLogout = async () => {
    try {
      await supabase.auth.signOut();
      toast.success("Uitgelogd");
      navigate("/map", { replace: true });
    } catch (error) {
      toast.error("Uitloggen mislukt", {
        description: error instanceof Error ? error.message : "Onbekende fout",
      });
    }
  };

  const cycleTheme = () => {
    const order: ThemeSetting[] = ["light", "dark", "system"];
    const currentIndex = order.indexOf(theme);
    const next = order[(currentIndex >= 0 ? currentIndex + 1 : 0) % order.length];
    setThemeState(next);
    setTheme(next);
  };

  return (
    <AppViewportShell variant="content">
      <PageShell
        title="Account"
        subtitle={isAuthenticated ? `Ingelogd als ${email || "gebruiker"}` : "Maak een account aan om je activiteit bij te houden"}
        maxWidth="4xl"
      >
        {!isLoading && (
          <section className="rounded-3xl border border-border bg-card p-6 shadow-soft mb-6">
            {isAuthenticated ? (
              <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div className="space-y-1">
                  <h2 className="text-lg font-medium text-foreground">Account</h2>
                  <p className="text-sm text-muted-foreground">
                    {email || "Gebruiker"} ({userId?.slice(0, 8)}...)
                  </p>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleLogout}
                  className="inline-flex items-center gap-2"
                >
                  <Icon name="LogOut" className="h-4 w-4" aria-hidden />
                  <span>Uitloggen</span>
                </Button>
              </div>
            ) : (
              <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div className="space-y-1">
                  <h2 className="text-lg font-medium text-foreground">Niet ingelogd</h2>
                  <p className="text-sm text-muted-foreground">
                    Log in of maak een account aan om je activiteit bij te houden
                  </p>
                </div>
                <Button
                  type="button"
                  size="sm"
                  onClick={() => navigate("/auth")}
                  className="inline-flex items-center gap-2"
                >
                  <Icon name="LogIn" className="h-4 w-4" aria-hidden />
                  <span>Inloggen / Registreren</span>
                </Button>
              </div>
            )}
          </section>
        )}
        <section
          aria-labelledby="appearance-heading"
          className="rounded-3xl border border-border bg-card p-6 shadow-soft"
        >
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="space-y-1">
            <h2 id="appearance-heading" className="text-lg font-medium text-foreground">
              Appearance
            </h2>
            <p className="text-sm text-muted-foreground">
              Temporarily manage the theme from here while the header is removed.
            </p>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={cycleTheme}
            aria-label="Schakel thema"
            className="inline-flex items-center gap-2"
          >
            <Icon name="SunMoon" className="h-4 w-4" aria-hidden />
            <span>Theme: {theme}</span>
          </Button>
        </div>
      </section>
      
      <PrivacySettings />
      
      {isAuthenticated && (
        <section
          aria-labelledby="referral-heading"
          className="rounded-3xl border border-border bg-card p-6 shadow-soft"
        >
          <ReferralShare />
        </section>
      )}
      
      <section
        aria-labelledby="activity-history-heading"
        className="rounded-3xl border border-border bg-card p-6 shadow-soft"
      >
        <h2 id="activity-history-heading" className="text-lg font-medium text-foreground mb-4">
          Activiteitsgeschiedenis
        </h2>
        <ActivityHistory />
      </section>
      
      <section className="rounded-3xl border border-border bg-card p-6 shadow-soft">
        <div className="space-y-4">
          <h2 className="text-lg font-medium text-foreground">Legal</h2>
          <div className="flex flex-col gap-2">
            <a
              href="#/privacy"
              className="text-sm text-muted-foreground hover:text-foreground underline transition-colors"
            >
              Privacybeleid
            </a>
            <a
              href="#/terms"
              className="text-sm text-muted-foreground hover:text-foreground underline transition-colors"
            >
              Gebruiksvoorwaarden
            </a>
            <a
              href="#/guidelines"
              className="text-sm text-muted-foreground hover:text-foreground underline transition-colors"
            >
              Community Richtlijnen
            </a>
          </div>
        </div>
      </section>
      </PageShell>
    </AppViewportShell>
  );
}

