// Onboarding Screen 0: Cold Open / Intro
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/ui/cn";
import { useEffect, useState } from "react";
import { MascotteAvatar } from "./MascotteAvatar";

export interface OnboardingScreen0Props {
  onNext: () => void;
}

export function OnboardingScreen0({ onNext }: OnboardingScreen0Props) {
  const [showFirstText, setShowFirstText] = useState(false);
  const [showSecondText, setShowSecondText] = useState(false);

  useEffect(() => {
    // Show first text immediately
    setShowFirstText(true);
    // Show second text after 400ms delay
    const timer = setTimeout(() => {
      setShowSecondText(true);
    }, 400);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-white">
      {/* Map background with blur/zoom effect */}
      <div
        className="absolute inset-0 bg-gradient-to-br from-primary/5 via-white to-white"
        style={{
          backgroundImage: "url('data:image/svg+xml,%3Csvg width=\"100\" height=\"100\" xmlns=\"http://www.w3.org/2000/svg\"%3E%3Cpath d=\"M0 0h100v100H0z\" fill=\"%23f0f0f0\"/%3E%3Cpath d=\"M20 20h60v60H20z\" fill=\"%23e0e0e0\"/%3E%3C/svg%3E')",
          backgroundSize: "200px 200px",
          filter: "blur(20px) brightness(1.2)",
          transform: "scale(1.2)",
        }}
        aria-hidden="true"
      />

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center justify-center px-6 text-center">
        {/* Mascotte */}
        <div className="mb-8">
          <MascotteAvatar size="xl" />
        </div>

        {/* Text with animation */}
        <div className="mb-8 space-y-4">
          <h1
            className={cn(
              "text-3xl font-semibold text-foreground transition-opacity duration-500",
              showFirstText ? "opacity-100" : "opacity-0"
            )}
          >
            Hallo, dünya!
          </h1>
          <h2
            className={cn(
              "text-2xl font-medium text-muted-foreground transition-opacity duration-500",
              showSecondText ? "opacity-100" : "opacity-0"
            )}
          >
            Welkom in de Turkse wereld.
          </h2>
        </div>

        {/* Primary CTA */}
        <Button
          onClick={onNext}
          size="lg"
          variant="default"
          className="min-w-[200px]"
          aria-label="Naar de Turkse wereld"
        >
          Naar de Turkse wereld
        </Button>
      </div>
    </div>
  );
}
