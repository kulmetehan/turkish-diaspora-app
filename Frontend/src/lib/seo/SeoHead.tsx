// Frontend/src/lib/seo/SeoHead.tsx
// Hoofd SEO component met react-helmet-async

import { Helmet } from "react-helmet-async";
import { useLocation } from "react-router-dom";
import { getAbsoluteUrl, getCanonicalUrl, type SeoConfig } from "./seoConfig";

export interface SeoHeadProps extends Partial<SeoConfig> {
  title?: string;
  description?: string;
  ogImage?: string;
  ogType?: string;
  noindex?: boolean;
  canonical?: string;
}

const APP_NAME = "Turkspot";
const DEFAULT_OG_IMAGE = "/turkspotbot.png";
const DEFAULT_OG_TYPE = "website";

/**
 * SEO Head component voor dynamische meta tags
 */
export function SeoHead({
  title,
  description,
  ogImage = DEFAULT_OG_IMAGE,
  ogType = DEFAULT_OG_TYPE,
  noindex = false,
  canonical,
}: SeoHeadProps) {
  const location = useLocation();
  
  // Build full title with app name
  const fullTitle = title ? `${title} - ${APP_NAME}` : APP_NAME;
  
  // Generate canonical URL
  const canonicalUrl = canonical || getCanonicalUrl(location.pathname);
  
  // Generate absolute OG image URL
  const absoluteOgImage = ogImage?.startsWith("http") 
    ? ogImage 
    : getAbsoluteUrl(ogImage);
  
  // Generate absolute page URL
  const absolutePageUrl = getAbsoluteUrl(location.pathname);
  
  return (
    <Helmet>
      {/* Basic meta tags */}
      <title>{fullTitle}</title>
      {description && <meta name="description" content={description} />}
      
      {/* Robots */}
      {noindex && <meta name="robots" content="noindex, nofollow" />}
      
      {/* Canonical URL */}
      <link rel="canonical" href={canonicalUrl} />
      
      {/* Open Graph tags */}
      <meta property="og:title" content={fullTitle} />
      {description && <meta property="og:description" content={description} />}
      <meta property="og:image" content={absoluteOgImage} />
      <meta property="og:url" content={absolutePageUrl} />
      <meta property="og:type" content={ogType} />
      <meta property="og:site_name" content={APP_NAME} />
      
      {/* Twitter Card tags */}
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={fullTitle} />
      {description && <meta name="twitter:description" content={description} />}
      <meta name="twitter:image" content={absoluteOgImage} />
      
      {/* Language alternates */}
      <link rel="alternate" hrefLang="nl" href={absolutePageUrl} />
      <link rel="alternate" hrefLang="en" href={absolutePageUrl} />
      <link rel="alternate" hrefLang="x-default" href={absolutePageUrl} />
    </Helmet>
  );
}



