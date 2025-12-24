// Onboarding Screen 1: Uitleg scherm met 3 feature bullets
import { Button } from "@/components/ui/button";
import { MascotteAvatar } from "./MascotteAvatar";

export interface OnboardingScreen1Props {
  onNext: () => void;
}

export function OnboardingScreen1({ onNext }: OnboardingScreen1Props) {
  return (
    <div className="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-background px-6">
      {/* Mascotte */}
      <div className="mb-8">
        <MascotteAvatar size="xl" />
      </div>

      {/* Feature bullets */}
      <div className="mb-8 space-y-6 w-full max-w-md">
        <div className="flex flex-col items-center text-center space-y-2">
          <div className="text-2xl font-gilroy font-semibold text-foreground">
            Nieuws
          </div>
          <div className="text-lg font-gilroy font-normal text-muted-foreground">
            → Uit Turkije & Nederland
          </div>
        </div>

        <div className="flex flex-col items-center text-center space-y-2">
          <div className="text-2xl font-gilroy font-semibold text-foreground">
            Locaties
          </div>
          <div className="text-lg font-gilroy font-normal text-muted-foreground">
            → Alle Turkse hotspots in Nederland
          </div>
        </div>

        <div className="flex flex-col items-center text-center space-y-2">
          <div className="text-2xl font-gilroy font-semibold text-foreground">
            Events
          </div>
          <div className="text-lg font-gilroy font-normal text-muted-foreground">
            → Wat is er deze week te doen?
          </div>
        </div>
      </div>

      {/* Primary CTA */}
      <Button
        onClick={onNext}
        size="lg"
        variant="default"
        className="min-w-[200px] font-gilroy"
        aria-label="Open de App"
      >
        Open de App
      </Button>
    </div>
  );
}


