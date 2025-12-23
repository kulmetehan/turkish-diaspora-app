// Frontend/src/components/rewards/RewardModal.tsx
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { getMyPendingRewards, claimReward, type UserReward } from "@/lib/api";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Gift } from "lucide-react";

interface RewardModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  reward?: UserReward | null;
}

export function RewardModal({ open, onOpenChange, reward: initialReward }: RewardModalProps) {
  const navigate = useNavigate();
  const [reward, setReward] = useState<UserReward | null>(initialReward || null);
  const [isLoading, setIsLoading] = useState(false);
  const [isClaiming, setIsClaiming] = useState(false);
  const [showClaimDetails, setShowClaimDetails] = useState(false);

  useEffect(() => {
    if (!open) {
      setReward(initialReward || null);
      setShowClaimDetails(false);
      return;
    }

    // If no initial reward provided, fetch the first pending reward
    if (!initialReward) {
      let cancelled = false;

      const fetchPendingReward = async () => {
        try {
          setIsLoading(true);
          const rewards = await getMyPendingRewards();
          if (!cancelled && rewards.length > 0) {
            setReward(rewards[0]);
          } else if (!cancelled) {
            // No pending rewards, close modal
            onOpenChange(false);
          }
        } catch (err) {
          if (!cancelled) {
            toast.error("Rewards konden niet worden geladen");
            onOpenChange(false);
          }
        } finally {
          if (!cancelled) {
            setIsLoading(false);
          }
        }
      };

      fetchPendingReward();

      return () => {
        cancelled = true;
      };
    } else {
      setReward(initialReward);
    }
  }, [open, initialReward, onOpenChange]);

  const handleClaim = async () => {
    if (!reward || isClaiming) return;

    try {
      setIsClaiming(true);
      const result = await claimReward(reward.id);

      if (result.success && result.reward) {
        // Update reward status
        setReward({
          ...reward,
          status: "claimed",
          claimed_at: result.reward.claimed_at,
          reward: result.reward,
        });
        toast.success("Reward succesvol geclaimed!");
        setShowClaimDetails(false);
      } else {
        toast.error(result.message || "Kon reward niet claimen");
      }
    } catch (err) {
      toast.error("Kon reward niet claimen");
    } finally {
      setIsClaiming(false);
    }
  };

  const handleHowToClaim = () => {
    setShowClaimDetails(true);
  };

  if (!reward) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <Gift className="h-5 w-5 text-primary" />
            <DialogTitle>Küçük bir teşekkür var.</DialogTitle>
          </div>
          <DialogDescription>
            Bu hafta katkın için {reward.reward.sponsor} tarafından ikram.
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="py-8 text-center text-muted-foreground">Reward laden...</div>
        ) : (
          <div className="space-y-4">
            <div className="rounded-lg bg-muted/50 p-4">
              <h3 className="font-semibold mb-2">{reward.reward.title}</h3>
              {reward.reward.description && (
                <p className="text-sm text-muted-foreground">
                  {reward.reward.description}
                </p>
              )}
            </div>

            {showClaimDetails && (
              <div className="rounded-lg border p-4 space-y-3">
                <h4 className="font-medium text-sm">Hoe claim je deze reward?</h4>
                <p className="text-sm text-muted-foreground">
                  {reward.reward.description || 
                    `Bezoek ${reward.reward.sponsor} en laat je reward zien.`}
                </p>
                {reward.status === "pending" && (
                  <Button
                    onClick={handleClaim}
                    disabled={isClaiming}
                    className="w-full"
                  >
                    {isClaiming ? "Claimen..." : "Claim reward"}
                  </Button>
                )}
              </div>
            )}

            {reward.status === "claimed" && (
              <div className="rounded-lg bg-green-500/10 border border-green-500/20 p-4">
                <p className="text-sm text-green-600 font-medium">
                  ✓ Deze reward is geclaimed op{" "}
                  {reward.claimed_at
                    ? new Date(reward.claimed_at).toLocaleDateString("nl-NL")
                    : "onbekende datum"}
                </p>
              </div>
            )}
          </div>
        )}

        <DialogFooter>
          {reward.status === "pending" && !showClaimDetails && (
            <>
              <Button
                variant="outline"
                onClick={handleHowToClaim}
              >
                Nasıl alırım?
              </Button>
              <Button
                variant="ghost"
                onClick={() => onOpenChange(false)}
              >
                Teşekkürler
              </Button>
            </>
          )}
          {reward.status === "pending" && showClaimDetails && (
            <Button
              variant="ghost"
              onClick={() => {
                setShowClaimDetails(false);
                onOpenChange(false);
              }}
            >
              Sluiten
            </Button>
          )}
          {reward.status === "claimed" && (
            <Button
              variant="ghost"
              onClick={() => onOpenChange(false)}
            >
              Sluiten
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}


