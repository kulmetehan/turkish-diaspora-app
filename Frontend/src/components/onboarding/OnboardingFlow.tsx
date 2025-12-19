// Onboarding Flow - Main orchestrator component
import { useNewsCityPreferences } from "@/hooks/useNewsCityPreferences";
import { completeOnboarding, type OnboardingData } from "@/lib/api";
import { useState } from "react";
import { toast } from "sonner";
import { OnboardingScreen0 } from "./OnboardingScreen0";
import { OnboardingScreen1 } from "./OnboardingScreen1";
import { OnboardingScreen2 } from "./OnboardingScreen2";
import { OnboardingScreen3 } from "./OnboardingScreen3";
import { OnboardingScreen4 } from "./OnboardingScreen4";
import { OnboardingScreen5 } from "./OnboardingScreen5";

export interface OnboardingFlowProps {
  onComplete: () => void;
}

interface OnboardingState {
  home_city?: string;
  home_region?: string;
  home_city_key?: string;
  memleket?: string[] | null;
  gender?: string | null;
}

export function OnboardingFlow({ onComplete }: OnboardingFlowProps) {
  const [currentScreen, setCurrentScreen] = useState(0);
  const [onboardingData, setOnboardingData] = useState<OnboardingState>({});
  const [isCompleting, setIsCompleting] = useState(false);

  // Hook for managing news city preferences
  const { savePreferences, rememberCityLabels } = useNewsCityPreferences();

  const handleScreen0Next = () => {
    setCurrentScreen(1);
  };

  const handleScreen1Next = () => {
    setCurrentScreen(2);
  };

  const handleScreen2Next = (data: { home_city: string; home_region: string; home_city_key: string }) => {
    setOnboardingData((prev) => ({
      ...prev,
      home_city: data.home_city,
      home_region: data.home_region,
      home_city_key: data.home_city_key,
    }));
    setCurrentScreen(3);
  };

  const handleScreen3Next = (data: { memleket: string[] | null }) => {
    setOnboardingData((prev) => ({
      ...prev,
      memleket: data.memleket,
    }));
    setCurrentScreen(4);
  };

  const handleScreen4Next = (data: { gender: string | null }) => {
    setOnboardingData((prev) => ({
      ...prev,
      gender: data.gender,
    }));
    setCurrentScreen(5);
  };

  const handleScreen5Complete = async () => {
    if (isCompleting) return;

    setIsCompleting(true);

    try {
      const data: OnboardingData = {
        home_city: onboardingData.home_city || null,
        home_region: onboardingData.home_region || null,
        home_city_key: onboardingData.home_city_key || null,
        memleket: onboardingData.memleket || null,
        gender: (onboardingData.gender as "male" | "female" | "prefer_not_to_say" | null) || null,
      };

      // Save to backend API (with localStorage fallback)
      await completeOnboarding(data);

      // Set news city preferences from onboarding data
      if (data.home_city_key || data.memleket) {
        const cityPreferences = {
          nl: data.home_city_key ? [data.home_city_key.toLowerCase()] : [],
          tr: data.memleket ? data.memleket.slice(0, 2).map(key => key.toLowerCase()) : [],
        };

        // Remember city labels for the selected cities
        if (data.home_city_key) {
          rememberCityLabels([{
            key: data.home_city_key.toLowerCase(),
            name: data.home_city || "",
            country: "nl",
          }]);
        }

        if (data.memleket && data.memleket.length > 0) {
          // Note: We don't have the full city info here, but the labels will be loaded
          // when the user visits the news page. For now, we just save the keys.
          rememberCityLabels(data.memleket.slice(0, 2).map(key => ({
            key: key.toLowerCase(),
            name: key, // Will be replaced when city data is loaded
            country: "tr",
          })));
        }

        // Save preferences
        savePreferences(cityPreferences);
      }

      toast.success("Onboarding voltooid!");
      onComplete();
    } catch (error) {
      console.error("Failed to complete onboarding:", error);
      toast.error("Kon onboarding niet voltooien. Probeer het opnieuw.");
      setIsCompleting(false);
    }
  };

  // Render current screen
  switch (currentScreen) {
    case 0:
      return <OnboardingScreen0 onNext={handleScreen0Next} />;
    case 1:
      return <OnboardingScreen1 onNext={handleScreen1Next} />;
    case 2:
      return <OnboardingScreen2 onNext={handleScreen2Next} onPrevious={() => setCurrentScreen(1)} />;
    case 3:
      return <OnboardingScreen3 onNext={handleScreen3Next} />;
    case 4:
      return <OnboardingScreen4 onNext={handleScreen4Next} />;
    case 5:
      return <OnboardingScreen5 onComplete={handleScreen5Complete} />;
    default:
      return null;
  }
}

