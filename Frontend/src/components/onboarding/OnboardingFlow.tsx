// Onboarding Flow - Main orchestrator component
import { useNewsCityPreferences } from "@/hooks/useNewsCityPreferences";
import { useUserAuth } from "@/hooks/useUserAuth";
import { completeOnboarding, type OnboardingData } from "@/lib/api";
import {
  trackOnboardingStarted,
  trackOnboardingScreenViewed,
  trackOnboardingDataCollected,
  trackOnboardingCompleted,
  trackOnboardingAbandoned,
} from "@/lib/analytics";
import { useEffect, useState, useRef } from "react";
import { toast } from "sonner";
import { OnboardingScreen0 } from "./OnboardingScreen0";
import { OnboardingScreen1 } from "./OnboardingScreen1";
import { OnboardingScreen2 } from "./OnboardingScreen2";
import { OnboardingScreen3 } from "./OnboardingScreen3";
import { OnboardingScreen4 } from "./OnboardingScreen4";
import { OnboardingScreen5 } from "./OnboardingScreen5";
import { OnboardingScreen6 } from "./OnboardingScreen6";

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
  
  // Check authentication status to conditionally show Screen 6
  const { isAuthenticated } = useUserAuth();

  // Track onboarding timing
  const startTimeRef = useRef<number>(Date.now());
  const screenStartTimeRef = useRef<number>(Date.now());
  const screenNames = [
    "welcome",
    "explanation",
    "home_city",
    "memleket",
    "gender",
    "success",
    "username_avatar",
  ];

  const handleScreen0Next = () => {
    setCurrentScreen(1);
  };

  const handleScreen1Next = () => {
    setCurrentScreen(2);
  };

  const handleScreen2Next = (data: { home_city: string; home_region: string; home_city_key: string }) => {
    // Track data collection
    trackOnboardingDataCollected(2, "home_city", "home_city", data.home_city);
    
    setOnboardingData((prev) => ({
      ...prev,
      home_city: data.home_city,
      home_region: data.home_region,
      home_city_key: data.home_city_key,
    }));
    setCurrentScreen(3);
  };

  const handleScreen3Next = (data: { memleket: string[] | null }) => {
    // Track data collection
    trackOnboardingDataCollected(3, "memleket", "memleket", data.memleket);
    
    setOnboardingData((prev) => ({
      ...prev,
      memleket: data.memleket,
    }));
    setCurrentScreen(4);
  };

  const handleScreen4Next = (data: { gender: string | null }) => {
    // Track data collection
    trackOnboardingDataCollected(4, "gender", "gender", data.gender);
    
    setOnboardingData((prev) => ({
      ...prev,
      gender: data.gender,
    }));
    setCurrentScreen(5);
  };

  const handleScreen5Next = () => {
    // Only proceed to Screen 6 if user is authenticated
    if (isAuthenticated) {
      setCurrentScreen(6);
    } else {
      // For anonymous users, complete onboarding directly
      handleScreen5Complete();
    }
  };

  const handleScreen6Complete = async () => {
    // Screen 6 handles its own profile update, so we just complete onboarding
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

      // Track completion
      const totalDuration = Date.now() - startTimeRef.current;
      trackOnboardingCompleted(
        {
          home_city: data.home_city,
          home_city_key: data.home_city_key,
          memleket: data.memleket,
          gender: data.gender,
          has_username: true, // Screen 6 is for authenticated users
          has_avatar: true, // Screen 6 includes avatar upload
        },
        totalDuration,
        7 // All screens completed (0-6)
      );

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

      // Track completion (for anonymous users, screen 5 is the last screen)
      const totalDuration = Date.now() - startTimeRef.current;
      trackOnboardingCompleted(
        {
          home_city: data.home_city,
          home_city_key: data.home_city_key,
          memleket: data.memleket,
          gender: data.gender,
          has_username: false, // Screen 5 is for anonymous users
          has_avatar: false,
        },
        totalDuration,
        6 // Screens 0-5 completed
      );

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

  // Track onboarding start
  useEffect(() => {
    trackOnboardingStarted();
    startTimeRef.current = Date.now();
    screenStartTimeRef.current = Date.now();
  }, []);

  // Track screen views when currentScreen changes
  useEffect(() => {
    if (currentScreen > 0) {
      const timeOnPreviousScreen = Date.now() - screenStartTimeRef.current;
      trackOnboardingScreenViewed(
        currentScreen,
        screenNames[currentScreen] || `screen_${currentScreen}`,
        timeOnPreviousScreen
      );
      screenStartTimeRef.current = Date.now();
    }
  }, [currentScreen]);

  // Track abandonment if component unmounts before completion
  useEffect(() => {
    return () => {
      if (!isCompleting) {
        const duration = Date.now() - startTimeRef.current;
        trackOnboardingAbandoned(
          currentScreen,
          screenNames[currentScreen] || `screen_${currentScreen}`,
          "navigate_away",
          duration
        );
      }
    };
  }, [currentScreen, isCompleting]);

  // Safety check: If we're on Screen 6 but user is not authenticated, complete onboarding
  useEffect(() => {
    if (currentScreen === 6 && !isAuthenticated) {
      handleScreen5Complete();
    }
  }, [currentScreen, isAuthenticated]);

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
      return (
        <OnboardingScreen5 
          onNext={isAuthenticated ? handleScreen5Next : undefined}
          onComplete={handleScreen5Complete}
        />
      );
    case 6:
      // Screen 6 only for authenticated users
      if (isAuthenticated) {
        return <OnboardingScreen6 onComplete={handleScreen6Complete} />;
      } else {
        // Fallback: return null (useEffect will handle completing onboarding)
        return null;
      }
    default:
      return null;
  }
}







