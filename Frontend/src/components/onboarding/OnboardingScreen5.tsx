// Onboarding Screen 5: Success/Reward
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/ui/cn";
import { useEffect, useState } from "react";
import { MascotteAvatar } from "./MascotteAvatar";

export interface OnboardingScreen5Props {
  onComplete: () => void;
}

export function OnboardingScreen5({ onComplete }: OnboardingScreen5Props) {
  const [showFirstText, setShowFirstText] = useState(false);
  const [showSecondText, setShowSecondText] = useState(false);

  useEffect(() => {
    // Trigger confetti on mount (always trigger, not dependent on state)
    // Dynamically import and trigger confetti
    import("canvas-confetti").then((confetti) => {
      const duration = 3000;
      const animationEnd = Date.now() + duration;
      const defaults = { startVelocity: 30, spread: 360, ticks: 60, zIndex: 0 };

      function randomInRange(min: number, max: number) {
        return Math.random() * (max - min) + min;
      }

      const interval: NodeJS.Timeout = setInterval(function () {
        const timeLeft = animationEnd - Date.now();

        if (timeLeft <= 0) {
          return clearInterval(interval);
        }

        const particleCount = 50 * (timeLeft / duration);
        confetti.default({
          ...defaults,
          particleCount,
          origin: { x: randomInRange(0.1, 0.3), y: Math.random() - 0.2 },
        });
        confetti.default({
          ...defaults,
          particleCount,
          origin: { x: randomInRange(0.7, 0.9), y: Math.random() - 0.2 },
        });
      }, 250);
    });

    // Show first text immediately
    setShowFirstText(true);
    // Show second text after 300ms delay
    const timer = setTimeout(() => {
      setShowSecondText(true);
    }, 300);
    return () => clearTimeout(timer);
  }, []); // Empty dependency array - always run on mount

  return (
    <div className="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-background px-6">
      {/* Mascotte (larger) */}
      <div className="mb-8">
        <MascotteAvatar size="xl" />
      </div>

      {/* Text animation (line by line) */}
      <div className="mb-8 space-y-4 text-center">
        <h1
          className={cn(
            "text-4xl font-gilroy font-bold text-foreground transition-opacity duration-500",
            showFirstText ? "opacity-100" : "opacity-0"
          )}
        >
          Klaar.
        </h1>
        <h2
          className={cn(
            "text-2xl font-gilroy font-semibold text-muted-foreground transition-opacity duration-500",
            showSecondText ? "opacity-100" : "opacity-0"
          )}
        >
          Ontdek de Turkse wereld.
        </h2>
      </div>

      {/* Badge display */}
      <div className="mb-6 rounded-lg border border-primary/20 bg-primary/5 px-6 py-4">
        <div className="text-center">
          <div className="mb-2 text-2xl">🎉</div>
          <div className="font-semibold text-foreground">Titel ontgrendeld</div>
          <div className="text-lg text-primary">Nieuwkomer</div>
        </div>
      </div>

      {/* XP hint */}
      <div className="mb-8 text-center">
        <div className="text-sm text-muted-foreground">+10 XP</div>
      </div>

      {/* Primary CTA */}
      <Button
        onClick={onComplete}
        size="lg"
        variant="default"
        className="min-w-[200px] font-gilroy"
        aria-label="Naar de feed"
      >
        Naar de feed
      </Button>
    </div>
  );
}




