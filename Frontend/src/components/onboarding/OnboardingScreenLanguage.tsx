// Onboarding Screen Language: Taalkeuze
import { Button } from "@/components/ui/button";
import { MascotteAvatar } from "./MascotteAvatar";
import { useTranslation } from "@/hooks/useTranslation";
import { useState } from "react";

export interface OnboardingScreenLanguageProps {
  onNext: () => void;
}

export function OnboardingScreenLanguage({ onNext }: OnboardingScreenLanguageProps) {
  const { t, setLanguage } = useTranslation();
  const [selectedLang, setSelectedLang] = useState<"nl" | "tr" | null>(null);

  const handleLanguageSelect = (lang: "nl" | "tr") => {
    setSelectedLang(lang);
    setLanguage(lang);
    // Small delay for visual feedback before proceeding
    setTimeout(() => {
      onNext();
    }, 300);
  };

  return (
    <div className="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-background px-6">
      {/* Mascotte */}
      <div className="mb-8">
        <MascotteAvatar size="xl" />
      </div>

      {/* Title */}
      <div className="mb-8 space-y-2 text-center">
        <h1 className="text-3xl font-gilroy font-bold text-foreground">
          {t("onboarding.language.title")}
        </h1>
        <p className="text-lg font-gilroy font-normal text-muted-foreground">
          {t("onboarding.language.subtitle")}
        </p>
      </div>

      {/* Language buttons */}
      <div className="w-full max-w-md space-y-4">
        <Button
          onClick={() => handleLanguageSelect("nl")}
          size="lg"
          variant={selectedLang === "nl" ? "default" : "outline"}
          className="w-full font-gilroy text-lg h-14"
          type="button"
        >
          {t("onboarding.language.dutch")}
        </Button>
        <Button
          onClick={() => handleLanguageSelect("tr")}
          size="lg"
          variant={selectedLang === "tr" ? "default" : "outline"}
          className="w-full font-gilroy text-lg h-14"
          type="button"
        >
          {t("onboarding.language.turkish")}
        </Button>
      </div>
    </div>
  );
}



