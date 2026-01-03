// Frontend/src/lib/seo/useSeo.ts
// Hook voor SEO management per route

import { useLocation } from "react-router-dom";
import { getSeoConfigForRoute, type SeoConfig } from "./seoConfig";

export interface UseSeoOptions {
  title?: string;
  description?: string;
  ogImage?: string;
  noindex?: boolean;
  canonical?: string;
}

/**
 * Hook die route detecteert en juiste SEO config ophaalt
 * Kan worden overschreven met custom options
 */
export function useSeo(options?: UseSeoOptions): SeoConfig {
  const location = useLocation();
  
  // Get route-based config
  const routeConfig = getSeoConfigForRoute(location.pathname);
  
  // Merge with custom options (options take precedence)
  return {
    ...routeConfig,
    ...options,
  };
}






