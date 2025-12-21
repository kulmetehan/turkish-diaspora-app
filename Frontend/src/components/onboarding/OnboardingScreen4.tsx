// Onboarding Screen 4: Geslacht Selector
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/ui/cn";
import { useEffect, useState } from "react";
import { MascotteAvatar } from "./MascotteAvatar";

export interface OnboardingScreen4Props {
  onNext: (data: { gender: string | null }) => void;
}

export function OnboardingScreen4({ onNext }: OnboardingScreen4Props) {
  const [selectedGender, setSelectedGender] = useState<string | null>(null);

  // Auto-advance after selection
  useEffect(() => {
    if (selectedGender) {
      const timer = setTimeout(() => {
        onNext({ gender: selectedGender });
      }, 300); // Small delay for visual feedback
      return () => clearTimeout(timer);
    }
  }, [selectedGender, onNext]);

  const handleSelect = (gender: string) => {
    setSelectedGender(gender);
  };

  return (
    <div className="fixed inset-0 z-[100] flex flex-col bg-background">
      {/* Header */}
      <div className="flex flex-col items-center justify-center px-6 pt-12 pb-8">
        <MascotteAvatar size="lg" className="mb-4" />
        <h2 className="mb-2 text-2xl font-gilroy font-bold text-foreground text-center">
          Zodat ik je op maat kan bedienen.
        </h2>
      </div>

      {/* Gender buttons */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 space-y-4">
        <p className="text-sm text-muted-foreground mb-4">Geslacht</p>
        <Button
          onClick={() => handleSelect("male")}
          size="lg"
          variant={selectedGender === "male" ? "default" : "outline"}
          className={cn(
            "w-full font-gilroy",
            selectedGender === "male" && "ring-2 ring-primary ring-offset-2"
          )}
          type="button"
        >
          Man
        </Button>
        <Button
          onClick={() => handleSelect("female")}
          size="lg"
          variant={selectedGender === "female" ? "default" : "outline"}
          className={cn(
            "w-full font-gilroy",
            selectedGender === "female" && "ring-2 ring-primary ring-offset-2"
          )}
          type="button"
        >
          Vrouw
        </Button>
        <Button
          onClick={() => handleSelect("prefer_not_to_say")}
          size="lg"
          variant={selectedGender === "prefer_not_to_say" ? "default" : "outline"}
          className={cn(
            "w-full font-gilroy",
            selectedGender === "prefer_not_to_say" && "ring-2 ring-primary ring-offset-2"
          )}
          type="button"
        >
          Zeg ik liever niet
        </Button>
      </div>
    </div>
  );
}




