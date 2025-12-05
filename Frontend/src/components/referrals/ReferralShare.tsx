// Frontend/src/components/referrals/ReferralShare.tsx
import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Icon } from "@/components/Icon";
import { Skeleton } from "@/components/ui/skeleton";
import { getMyReferralCode, getReferralStats, type ReferralCode, type ReferralStats } from "@/lib/api";
import { toast } from "sonner";
import { ShareButton } from "@/components/share/ShareButton";
import { share } from "@/lib/share";
import { useUserAuth } from "@/hooks/useUserAuth";

export function ReferralShare() {
  const { isAuthenticated } = useUserAuth();
  const [referralCode, setReferralCode] = useState<ReferralCode | null>(null);
  const [stats, setStats] = useState<ReferralStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      loadReferralData();
    } else {
      setLoading(false);
    }
  }, [isAuthenticated]);

  const loadReferralData = async () => {
    setLoading(true);
    try {
      const [codeData, statsData] = await Promise.all([
        getMyReferralCode().catch(() => null),
        getReferralStats().catch(() => null),
      ]);
      setReferralCode(codeData);
      setStats(statsData);
    } catch (err) {
      toast.error("Kon referral data niet laden", {
        description: err instanceof Error ? err.message : "Onbekende fout",
      });
    } finally {
      setLoading(false);
    }
  };

  const referralLink = referralCode
    ? `${window.location.origin}${window.location.pathname}#/auth?ref=${referralCode.code}`
    : "";

  const handleCopyLink = async () => {
    if (!referralLink) return;

    try {
      await navigator.clipboard.writeText(referralLink);
      setCopied(true);
      toast.success("Link gekopieerd naar klembord!");
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      toast.error("Kon link niet kopiëren", {
        description: "Probeer het opnieuw of deel handmatig.",
      });
    }
  };

  const handleShare = async () => {
    if (!referralCode) return;

    const shareUrl = referralLink;
    const success = await share({
      title: "Join Turkspot!",
      text: `Check out Turkspot - the Turkish diaspora community app! Use my referral code: ${referralCode.code}`,
      url: shareUrl,
    });

    if (success && typeof navigator !== "undefined" && !("share" in navigator)) {
      toast.success("Link gekopieerd!");
    }
  };

  if (!isAuthenticated) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Referral Programma</CardTitle>
          <CardDescription>
            Log in om je eigen referral code te krijgen en vrienden uit te nodigen
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Referral Programma</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-10 w-full mb-4" />
          <Skeleton className="h-24 w-full" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Icon name="Users" className="h-5 w-5" />
          Referral Programma
        </CardTitle>
        <CardDescription>
          Nodig vrienden uit en verdien XP wanneer zij zich aanmelden
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {referralCode ? (
          <>
            <div className="space-y-2">
              <label className="text-sm font-medium">Je Referral Code</label>
              <div className="flex gap-2">
                <Input
                  value={referralCode.code}
                  readOnly
                  className="font-mono text-lg font-bold text-center"
                />
                <Button
                  variant="outline"
                  size="icon"
                  onClick={handleCopyLink}
                  aria-label="Kopieer code"
                >
                  <Icon name={copied ? "Check" : "Copy"} className="h-4 w-4" />
                </Button>
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Je Referral Link</label>
              <div className="flex gap-2">
                <Input value={referralLink} readOnly className="text-sm" />
                <Button
                  variant="outline"
                  onClick={handleCopyLink}
                  size="sm"
                >
                  {copied ? "Gekopieerd!" : "Kopieer"}
                </Button>
              </div>
            </div>

            <div className="flex gap-2">
              <ShareButton
                customData={{
                  title: "Join Turkspot!",
                  text: `Check out Turkspot - the Turkish diaspora community app! Use my referral code: ${referralCode.code}`,
                  url: referralLink,
                }}
                className="flex-1"
              />
            </div>

            {stats && (
              <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                <div>
                  <p className="text-sm text-muted-foreground">Totaal Referrals</p>
                  <p className="text-2xl font-bold">{stats.total_referrals}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Laatste 30 dagen</p>
                  <p className="text-2xl font-bold">{stats.referrals_last_30d}</p>
                </div>
              </div>
            )}

            <div className="text-xs text-muted-foreground pt-2">
              <p>• Je krijgt 50 XP wanneer iemand je referral code gebruikt</p>
              <p>• Je vriend krijgt 25 XP welcome bonus</p>
              <p>• Maximaal 1 referral code per gebruiker</p>
            </div>
          </>
        ) : (
          <div className="text-center text-muted-foreground py-4">
            <p>Kon referral code niet laden. Probeer het opnieuw.</p>
            <Button
              variant="outline"
              size="sm"
              onClick={loadReferralData}
              className="mt-4"
            >
              Opnieuw proberen
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

