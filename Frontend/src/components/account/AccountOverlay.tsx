import { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";

import { AccountLoginSection } from "@/components/account/AccountLoginSection";
import { AccountTabs, type AccountTabKey } from "@/components/account/AccountTabs";
import { LanguageSwitcher } from "@/components/account/LanguageSwitcher";
import { AboutUsSection } from "@/components/account/AboutUsSection";
import { ProfileSection } from "@/components/account/ProfileSection";
import { UserRolesSection } from "@/components/account/UserRolesSection";
import { UserLocationsSection } from "@/components/account/UserLocationsSection";
import { RhythmSection } from "@/components/account/RhythmSection";
import { ContributionsSection } from "@/components/account/ContributionsSection";
import { RecognitionSection } from "@/components/account/RecognitionSection";
import { ActivityHistory } from "@/components/activity/ActivityHistory";
import { PushNotificationSettings } from "@/components/push/PushNotificationSettings";
import { PrivacySettings } from "@/components/settings/PrivacySettings";
import { RewardModal } from "@/components/rewards/RewardModal";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/Icon";
import { cn } from "@/lib/ui/cn";
import { useTranslation } from "@/hooks/useTranslation";
import { useUserAuth } from "@/hooks/useUserAuth";
import { supabase } from "@/lib/supabaseClient";
import { getMyPendingRewards, type UserReward } from "@/lib/api";
import { getTheme, setTheme, type ThemeSetting } from "@/lib/theme/darkMode";
import { toast } from "sonner";

interface AccountOverlayProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AccountOverlay({ open, onOpenChange }: AccountOverlayProps) {
  const { t } = useTranslation();
  const [theme, setThemeState] = useState<ThemeSetting>("system");
  const [activeTab, setActiveTab] = useState<AccountTabKey>("weergave");
  const { isAuthenticated, userId, email, isLoading } = useUserAuth();
  const navigate = useNavigate();
  const [pendingReward, setPendingReward] = useState<UserReward | null>(null);
  const [rewardModalOpen, setRewardModalOpen] = useState(false);
  const rewardCheckIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const hasCheckedRewardsRef = useRef(false);

  useEffect(() => {
    setThemeState(getTheme());
  }, []);

  // Reset activeTab if it's set to removed "referral" tab
  useEffect(() => {
    const validTabs: AccountTabKey[] = ["weergave", "privacy", "notificaties", "geschiedenis", "over_ons"];
    if (!validTabs.includes(activeTab)) {
      setActiveTab("weergave");
    }
  }, [activeTab]);

  // Check for pending rewards on mount and periodically
  useEffect(() => {
    if (!isAuthenticated || isLoading || !open) {
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
  }, [isAuthenticated, isLoading, open]);

  const handleLogout = async () => {
    try {
      await supabase.auth.signOut();
      toast.success("Uitgelogd");
      onOpenChange(false);
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

  return (
    <>
      <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
        <DialogPrimitive.Portal>
          <DialogPrimitive.Overlay
            className={cn(
              "fixed inset-0 z-[55] bg-black/40 backdrop-blur",
              "pointer-events-none data-[state=open]:pointer-events-auto",
              "data-[state=closed]:animate-out data-[state=closed]:fade-out-0",
              "data-[state=open]:animate-in data-[state=open]:fade-in-0",
            )}
          />
          <DialogPrimitive.Content
            className={cn(
              "fixed inset-x-0 bottom-0 top-auto z-[60] mx-auto w-full max-w-screen-sm",
              "flex max-h-[min(90vh,800px)] flex-col rounded-t-[40px] border border-white/15 bg-surface-raised/95 text-foreground shadow-[0_-40px_80px_rgba(0,0,0,0.6)] backdrop-blur-2xl",
              "px-5 pt-6 pb-[calc(env(safe-area-inset-bottom)+20px)]",
              "focus:outline-none data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:slide-in-from-bottom",
              "data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:slide-out-to-bottom",
              "lg:left-1/2 lg:right-auto lg:top-1/2 lg:bottom-auto lg:max-h-[85vh] lg:w-[min(90vw,840px)] lg:max-w-[min(90vw,840px)] lg:-translate-x-1/2 lg:-translate-y-1/2",
              "lg:rounded-[40px] lg:px-6 lg:pb-6 lg:shadow-[0_45px_90px_rgba(0,0,0,0.6)]",
              "lg:data-[state=open]:zoom-in-95 lg:data-[state=closed]:zoom-out-95",
            )}
            aria-labelledby="account-overlay-title"
          >
            <div className="flex items-center justify-between mb-4 pb-4 border-b border-white/10">
              <DialogPrimitive.Title
                id="account-overlay-title"
                className="text-2xl font-semibold tracking-tight"
              >
                Account
              </DialogPrimitive.Title>
              <DialogPrimitive.Description className="sr-only">
                {t("account.tabs.general")}
              </DialogPrimitive.Description>
              <DialogPrimitive.Close className="rounded-sm opacity-70 transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-primary/30">
                <X className="h-5 w-5" aria-label="Sluiten" />
              </DialogPrimitive.Close>
            </div>

            <div className="flex-1 overflow-y-auto -mx-5 px-5">
              <div className="max-w-4xl mx-auto py-4">
                <AccountTabs value={activeTab} onChange={setActiveTab} className="mb-4" />

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
                        <RhythmSection className="mb-4" />
                        <ContributionsSection className="mb-4" />
                        <RecognitionSection className="mb-4" />
                      </>
                    )}

                    {/* Display settings: Language and Theme */}
                    <div className="rounded-xl bg-surface-muted/50 p-6 mb-4">
                      <div className="space-y-4">
                        <div className="space-y-1">
                          <h2 className="text-lg font-gilroy font-medium text-foreground">
                            {t("account.display.title")}
                          </h2>
                          <p className="text-sm text-muted-foreground">
                            {t("account.display.description")}
                          </p>
                        </div>
                        
                        {/* Language switcher */}
                        <div className="flex flex-col gap-2">
                          <label className="text-sm font-medium text-foreground">
                            {t("account.display.language")}
                          </label>
                          <div className="w-full">
                            <LanguageSwitcher />
                          </div>
                        </div>

                        {/* Theme switcher */}
                        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                          <label className="text-sm font-medium text-foreground">
                            {t("account.display.theme")}
                          </label>
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={cycleTheme}
                            aria-label={t("account.display.theme")}
                            className="inline-flex items-center gap-2 text-foreground w-full md:w-auto"
                          >
                            <Icon name="SunMoon" className="h-4 w-4" aria-hidden />
                            <span>{t("account.display.theme")} {theme}</span>
                          </Button>
                        </div>
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

                {activeTab === "over_ons" && (
                  <div className="rounded-xl bg-surface-muted/50 p-6">
                    <AboutUsSection />
                  </div>
                )}
              </div>
            </div>
          </DialogPrimitive.Content>
        </DialogPrimitive.Portal>
      </DialogPrimitive.Root>

      {/* Reward Modal */}
      {isAuthenticated && (
        <RewardModal
          open={rewardModalOpen}
          onOpenChange={setRewardModalOpen}
          reward={pendingReward}
        />
      )}
    </>
  );
}

