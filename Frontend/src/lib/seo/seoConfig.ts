// Frontend/src/lib/seo/seoConfig.ts
// Centrale SEO configuratie voor alle routes

export interface SeoConfig {
  title: string;
  description: string;
  ogImage?: string;
  ogType?: string;
  noindex?: boolean;
  canonical?: string;
}

const APP_NAME = "Turkspot";
const DEFAULT_DESCRIPTION = "Ontdek activiteiten, nieuws en updates van de Turkish gemeenschap in Nederland";
const DEFAULT_OG_IMAGE = "/turkspotbot.png";

// Helper om absolute URL te genereren
export function getAbsoluteUrl(path: string = ""): string {
  if (typeof window === "undefined") {
    return path;
  }
  
  const basePath = import.meta.env.BASE_URL || "/";
  const baseUrl = window.location.origin;
  
  // Remove trailing slash from basePath if present
  const cleanBasePath = basePath.endsWith("/") ? basePath.slice(0, -1) : basePath;
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  
  return `${baseUrl}${cleanBasePath}${cleanPath}`;
}

// Helper om canonical URL te genereren
export function getCanonicalUrl(path: string = ""): string {
  const hashPath = path.startsWith("#") ? path : `#${path}`;
  return getAbsoluteUrl(hashPath);
}

// Route-specifieke SEO configuratie
export const seoConfig: Record<string, SeoConfig> = {
  "/feed": {
    title: `Feed - ${APP_NAME}`,
    description: DEFAULT_DESCRIPTION,
    ogImage: DEFAULT_OG_IMAGE,
  },
  "/map": {
    title: `Kaart - ${APP_NAME}`,
    description: "Interactieve kaart met Turkish bedrijven en locaties in Nederlandse steden",
    ogImage: DEFAULT_OG_IMAGE,
  },
  "/news": {
    title: `Nieuws - ${APP_NAME}`,
    description: "Laatste nieuws uit Nederland en Turkije, speciaal voor de diaspora gemeenschap",
    ogImage: DEFAULT_OG_IMAGE,
  },
  "/events": {
    title: `Evenementen - ${APP_NAME}`,
    description: "Ontdek evenementen en activiteiten in de Turkish gemeenschap",
    ogImage: DEFAULT_OG_IMAGE,
  },
  "/account": {
    title: `Account - ${APP_NAME}`,
    description: "Beheer je profiel en instellingen",
    ogImage: DEFAULT_OG_IMAGE,
  },
  "/prikbord": {
    title: `Prikbord - ${APP_NAME}`,
    description: "Community prikbord met advertenties en aankondigingen",
    ogImage: DEFAULT_OG_IMAGE,
  },
  "/privacy": {
    title: `Privacybeleid - ${APP_NAME}`,
    description: "Privacybeleid en gegevensbescherming",
    ogImage: DEFAULT_OG_IMAGE,
  },
  "/terms": {
    title: `Algemene Voorwaarden - ${APP_NAME}`,
    description: "Algemene voorwaarden voor gebruik",
    ogImage: DEFAULT_OG_IMAGE,
  },
  "/guidelines": {
    title: `Community Richtlijnen - ${APP_NAME}`,
    description: "Richtlijnen voor de community",
    ogImage: DEFAULT_OG_IMAGE,
  },
  "/pulse": {
    title: `Diaspora Pulse - ${APP_NAME}`,
    description: "Pulse van de diaspora gemeenschap",
    ogImage: DEFAULT_OG_IMAGE,
  },
  "/auth": {
    title: `Inloggen / Registreren - ${APP_NAME}`,
    description: "Maak een account aan of log in",
    ogImage: DEFAULT_OG_IMAGE,
  },
  "/login": {
    title: `Inloggen - ${APP_NAME}`,
    description: "Log in op je account",
    ogImage: DEFAULT_OG_IMAGE,
  },
};

// Default SEO config
export const defaultSeoConfig: SeoConfig = {
  title: APP_NAME,
  description: DEFAULT_DESCRIPTION,
  ogImage: DEFAULT_OG_IMAGE,
  ogType: "website",
};

// Helper om SEO config te krijgen voor een route
export function getSeoConfigForRoute(path: string): SeoConfig {
  // Remove hash and query params
  const cleanPath = path.replace(/^#/, "").split("?")[0].split("/")[0] || "/";
  
  // Check exact match first
  if (seoConfig[cleanPath]) {
    return seoConfig[cleanPath];
  }
  
  // Check if it's a dynamic route (locations, polls, etc.)
  if (cleanPath.startsWith("/locations/")) {
    return {
      title: `Locatie - ${APP_NAME}`,
      description: "Bekijk details van deze locatie",
      ogImage: DEFAULT_OG_IMAGE,
    };
  }
  
  if (cleanPath.startsWith("/polls/")) {
    return {
      title: `Poll - ${APP_NAME}`,
      description: "Bekijk en stem op deze poll",
      ogImage: DEFAULT_OG_IMAGE,
    };
  }
  
  if (cleanPath.startsWith("/admin")) {
    return {
      title: `Admin - ${APP_NAME}`,
      description: "Admin dashboard",
      ogImage: DEFAULT_OG_IMAGE,
      noindex: true,
    };
  }
  
  return defaultSeoConfig;
}


