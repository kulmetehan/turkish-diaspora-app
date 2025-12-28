import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { AccountLoginSection } from "@/components/account/AccountLoginSection";
import { AccountTabs, type AccountTabKey } from "@/components/account/AccountTabs";
import { ContributionsSection } from "@/components/account/ContributionsSection";
import { ProfileSection } from "@/components/account/ProfileSection";
import { RecognitionSection } from "@/components/account/RecognitionSection";
import { RhythmSection } from "@/components/account/RhythmSection";
import { SeninSection } from "@/components/account/SeninSection";
import { UserRolesSection } from "@/components/account/UserRolesSection";
import { UserLocationsSection } from "@/components/account/UserLocationsSection";
import { ActivityHistory } from "@/components/activity/ActivityHistory";
import { AppHeader } from "@/components/feed/AppHeader";
import { FooterTabs } from "@/components/FooterTabs";
import { Icon } from "@/components/Icon";
import { AppViewportShell } from "@/components/layout";
import { PushNotificationSettings } from "@/components/push/PushNotificationSettings";
import { RewardModal } from "@/components/rewards/RewardModal";
import { PrivacySettings } from "@/components/settings/PrivacySettings";
import { Button } from "@/components/ui/button";
import { useUserAuth } from "@/hooks/useUserAuth";
import { getMyPendingRewards, type UserReward } from "@/lib/api";
import { supabase } from "@/lib/supabaseClient";
import { getTheme, setTheme, type ThemeSetting } from "@/lib/theme/darkMode";
import { toast } from "sonner";

export default function AccountPage() {
  const [theme, setThemeState] = useState<ThemeSetting>("system");
  const [activeTab, setActiveTab] = useState<AccountTabKey>("weergave");
  const { isAuthenticated, userId, email, isLoading } = useUserAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [pendingReward, setPendingReward] = useState<UserReward | null>(null);
  const [rewardModalOpen, setRewardModalOpen] = useState(false);
  const rewardCheckIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const hasCheckedRewardsRef = useRef(false);

  useEffect(() => {
    setThemeState(getTheme());
  }, []);

  // Read tab parameter from URL hash
  useEffect(() => {
    const validTabs: AccountTabKey[] = ["weergave", "privacy", "notificaties", "geschiedenis"];
    
    // Parse tab parameter from hash (e.g., #/account?tab=notificaties)
    const hash = location.hash || "";
    const queryIndex = hash.indexOf("?");
    if (queryIndex >= 0) {
      const queryString = hash.slice(queryIndex + 1);
      const params = new URLSearchParams(queryString);
      const tabParam = params.get("tab");
      
      if (tabParam && validTabs.includes(tabParam as AccountTabKey)) {
        setActiveTab(tabParam as AccountTabKey);
        return;
      }
    }
    
    // Fallback: validate current activeTab
    if (!validTabs.includes(activeTab)) {
      setActiveTab("weergave");
    }
  }, [location.hash]);

  // Update URL when tab changes
  const handleTabChange = (tab: AccountTabKey) => {
    setActiveTab(tab);
    // Update URL hash with tab parameter
    const newHash = `#/account?tab=${tab}`;
    window.history.replaceState(null, "", newHash);
  };

  // Redirect to login if not authenticated
  useEffect(() => {
    if (isLoading) {
      return; // Wait for auth check to complete
    }
    
    if (!isAuthenticated) {
      // Preserve current hash (including tab parameter) for return after login
      const returnUrl = location.hash || "#/account";
      navigate("/auth", { 
        state: { from: { pathname: "/account", hash: returnUrl } },
        replace: true 
      });
    }
  }, [isAuthenticated, isLoading, navigate, location.hash]);

  // Check for pending rewards on mount and periodically
  useEffect(() => {
    if (!isAuthenticated || isLoading) {
      return;
    }

    const checkRewards = async () => {
      try {
        const rewards = await getMyPendingRewards();
        if (rewards.length > 0 && !hasCheckedRewardsRef.current) {
          // Only show modal if we haven't checked before (first load)
          setPendingReward(rewards[0]);
          setRewardModalOpen(true);
          hasCheckedRewardsRef.current = true;
        } else if (rewards.length > 0) {
          // Update pending reward if it exists but don't auto-open modal
          setPendingReward(rewards[0]);
        } else {
          setPendingReward(null);
        }
      } catch (err) {
        // Silently fail - rewards are optional
        console.debug("Failed to check rewards:", err);
      }
    };

    // Check immediately on mount
    checkRewards();

    // Check periodically (every 5 minutes)
    rewardCheckIntervalRef.current = setInterval(checkRewards, 5 * 60 * 1000);

    return () => {
      if (rewardCheckIntervalRef.current) {
        clearInterval(rewardCheckIntervalRef.current);
      }
    };
  }, [isAuthenticated, isLoading]);

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
            <AccountTabs value={activeTab} onChange={handleTabChange} className="mb-4" />

            {activeTab === "weergave" && (
              <>
                {!isLoading && (
                  <AccountLoginSection
                    isAuthenticated={isAuthenticated}
                    email={email}
                    userId={userId}
                    onLogout={handleLogout}
                    className="mb-4"
                  />
                )}

                {/* Profile section - only show when authenticated */}
                {isAuthenticated && (
                  <ProfileSection className="mb-4" />
                )}

                {/* Gamification sections - only show when authenticated */}
                {isAuthenticated && (
                  <>
                    <UserRolesSection className="mb-4" />
                    <UserLocationsSection className="mb-4" />
                    <SeninSection className="mb-4" />
                    <RhythmSection className="mb-4" />
                    <ContributionsSection className="mb-4" />
                    <RecognitionSection className="mb-4" />
                  </>
                )}

                <div className="rounded-xl bg-surface-muted/50 p-6 mb-4">
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

                {/* Legal section */}
                <div className="rounded-xl bg-surface-muted/50 p-6">
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
              </>
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

            {activeTab === "geschiedenis" && (
              <div className="rounded-xl bg-surface-muted/50 p-6">
                <h2 className="text-lg font-gilroy font-medium text-foreground mb-4">
                  Activiteitsgeschiedenis
                </h2>
                <ActivityHistory />
              </div>
            )}
          </div>
        </div>
        <FooterTabs />
      </div>

      {/* Reward Modal */}
      {isAuthenticated && (
        <RewardModal
          open={rewardModalOpen}
          onOpenChange={setRewardModalOpen}
          reward={pendingReward}
        />
      )}
    </AppViewportShell>
  );
}

