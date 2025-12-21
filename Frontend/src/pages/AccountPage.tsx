import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { AccountLoginSection } from "@/components/account/AccountLoginSection";
import { AccountTabs, type AccountTabKey } from "@/components/account/AccountTabs";
import { ActivityHistory } from "@/components/activity/ActivityHistory";
import { AppHeader } from "@/components/feed/AppHeader";
import { FooterTabs } from "@/components/FooterTabs";
import { Icon } from "@/components/Icon";
import { AppViewportShell } from "@/components/layout";
import { PushNotificationSettings } from "@/components/push/PushNotificationSettings";
import { ReferralShare } from "@/components/referrals/ReferralShare";
import { PrivacySettings } from "@/components/settings/PrivacySettings";
import { Button } from "@/components/ui/button";
import { useUserAuth } from "@/hooks/useUserAuth";
import { supabase } from "@/lib/supabaseClient";
import { getTheme, setTheme, type ThemeSetting } from "@/lib/theme/darkMode";
import { toast } from "sonner";

export default function AccountPage() {
  const [theme, setThemeState] = useState<ThemeSetting>("system");
  const [activeTab, setActiveTab] = useState<AccountTabKey>("weergave");
  const { isAuthenticated, userId, email, isLoading } = useUserAuth();
  const navigate = useNavigate();

  useEffect(() => {
    setThemeState(getTheme());
  }, []);

  const handleLogout = async () => {
    try {
      await supabase.auth.signOut();
      toast.success("Uitgelogd");
      navigate("/feed", { replace: true });
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
    setTheme(next);
    setThemeState(next);
  };

  const handleNotificationClick = () => {
    // TODO: Implement notification navigation
    console.log("Notification clicked");
  };

  return (
    <AppViewportShell variant="content">
      <div className="flex flex-col h-full relative">
        {/* Red gradient overlay */}
        <div
          className="absolute inset-x-0 top-0 pointer-events-none z-0"
          style={{
            height: '25%',
            background: 'linear-gradient(180deg, hsl(var(--brand-red) / 0.10) 0%, hsl(var(--brand-red) / 0.03) 50%, transparent 100%)',
          }}
        />
        <AppHeader onNotificationClick={handleNotificationClick} />
        <div className="flex-1 overflow-y-auto px-4 pb-24 relative z-10">
          <div className="max-w-4xl mx-auto py-4">
            {!isLoading && (
              <AccountLoginSection
                isAuthenticated={isAuthenticated}
                email={email}
                userId={userId}
                onLogout={handleLogout}
                className="mb-4"
              />
            )}

            <AccountTabs value={activeTab} onChange={setActiveTab} className="mb-4" />

            {activeTab === "weergave" && (
              <div className="rounded-xl bg-surface-muted/50 p-6">
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                  <div className="space-y-1">
                    <h2 className="text-lg font-gilroy font-medium text-foreground">
                      Weergave
                    </h2>
                    <p className="text-sm text-muted-foreground">
                      Beheer het thema van de app
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={cycleTheme}
                    aria-label="Schakel thema"
                    className="inline-flex items-center gap-2 text-foreground"
                  >
                    <Icon name="SunMoon" className="h-4 w-4" aria-hidden />
                    <span>Theme: {theme}</span>
                  </Button>
                </div>
              </div>
            )}

            {activeTab === "privacy" && (
              <div className="rounded-xl bg-surface-muted/50 p-6">
                <PrivacySettings />
              </div>
            )}

            {activeTab === "notificaties" && (
              <div className="rounded-xl bg-surface-muted/50 p-6">
                <PushNotificationSettings />
              </div>
            )}

            {activeTab === "referral" && (
              isAuthenticated ? (
                <div className="rounded-xl bg-surface-muted/50 p-6">
                  <ReferralShare />
                </div>
              ) : (
                <div className="rounded-xl bg-surface-muted/50 p-6">
                  <div className="space-y-4">
                    <div>
                      <h2 className="text-lg font-gilroy font-medium text-foreground mb-1">Referral Programma</h2>
                      <p className="text-sm text-muted-foreground">
                        Nodig vrienden uit en verdien XP wanneer zij zich aanmelden
                      </p>
                    </div>
                    <div className="flex flex-col items-center justify-center py-8 px-4 text-center border border-dashed border-border rounded-lg bg-muted/30">
                      <Icon name="Users" className="h-12 w-12 text-muted-foreground mb-4" />
                      <h3 className="text-lg font-semibold mb-2">Inloggen vereist</h3>
                      <p className="text-sm text-muted-foreground mb-6 max-w-md">
                        Om het referral programma te gebruiken, heb je een account nodig.
                        Dit zorgt ervoor dat je referral code gekoppeld is aan jouw account.
                      </p>
                      <Button onClick={() => navigate("/auth")} className="inline-flex items-center gap-2">
                        <Icon name="LogIn" className="h-4 w-4" />
                        <span>Inloggen / Registreren</span>
                      </Button>
                    </div>
                  </div>
                </div>
              )
            )}

            {activeTab === "geschiedenis" && (
              <div className="rounded-xl bg-surface-muted/50 p-6">
                <h2 className="text-lg font-gilroy font-medium text-foreground mb-4">
                  Activiteitsgeschiedenis
                </h2>
                <ActivityHistory />
              </div>
            )}

            {/* Legal section at bottom without border */}
            <div className="mt-6 rounded-xl bg-surface-muted/50 p-6">
              <div className="space-y-4">
                <h2 className="text-lg font-gilroy font-medium text-foreground">Legal</h2>
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
            </div>
          </div>
        </div>
        <FooterTabs />
      </div>
    </AppViewportShell>
  );
}

