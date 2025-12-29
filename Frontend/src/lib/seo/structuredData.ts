// Frontend/src/lib/seo/structuredData.ts
// JSON-LD schema generators

import { getAbsoluteUrl } from "./seoConfig";

const APP_NAME = "Turkspot";
const DEFAULT_OG_IMAGE = "/turkspotbot.png";

export interface OrganizationSchema {
  "@context": string;
  "@type": string;
  name: string;
  url: string;
  logo?: string;
  description?: string;
}

export interface WebsiteSchema {
  "@context": string;
  "@type": string;
  name: string;
  url: string;
  potentialAction?: {
    "@type": string;
    target: {
      "@type": string;
      urlTemplate: string;
    };
    "query-input": string;
  };
}

export interface LocalBusinessSchema {
  "@context": string;
  "@type": string;
  name: string;
  address?: {
    "@type": string;
    streetAddress?: string;
    addressLocality?: string;
    addressRegion?: string;
    postalCode?: string;
    addressCountry?: string;
  };
  geo?: {
    "@type": string;
    latitude?: number;
    longitude?: number;
  };
  url?: string;
  image?: string;
  description?: string;
  telephone?: string;
  priceRange?: string;
  servesCuisine?: string;
  openingHours?: string[];
}

/**
 * Generate Organization schema
 */
export function generateOrganizationSchema(): OrganizationSchema {
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: APP_NAME,
    url: getAbsoluteUrl(),
    logo: getAbsoluteUrl(DEFAULT_OG_IMAGE),
    description: "Ontdek activiteiten, nieuws en updates van de Turkish gemeenschap in Nederland",
  };
}

/**
 * Generate Website schema
 */
export function generateWebsiteSchema(): WebsiteSchema {
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: APP_NAME,
    url: getAbsoluteUrl(),
  };
}

/**
 * Generate LocalBusiness schema for a location
 */
export function generateLocationSchema(location: {
  name: string;
  address?: string;
  city?: string;
  postal_code?: string;
  country?: string;
  latitude?: number;
  longitude?: number;
  category?: string;
  phone?: string;
  website?: string;
  image?: string;
  description?: string;
}): LocalBusinessSchema {
  const schema: LocalBusinessSchema = {
    "@context": "https://schema.org",
    "@type": "LocalBusiness",
    name: location.name,
  };
  
  // Address
  if (location.address || location.city || location.postal_code) {
    schema.address = {
      "@type": "PostalAddress",
    };
    
    if (location.address) {
      schema.address.streetAddress = location.address;
    }
    if (location.city) {
      schema.address.addressLocality = location.city;
    }
    if (location.postal_code) {
      schema.address.postalCode = location.postal_code;
    }
    if (location.country) {
      schema.address.addressCountry = location.country;
    } else {
      schema.address.addressCountry = "NL";
    }
  }
  
  // Geo coordinates
  if (location.latitude !== undefined && location.longitude !== undefined) {
    schema.geo = {
      "@type": "GeoCoordinates",
      latitude: location.latitude,
      longitude: location.longitude,
    };
  }
  
  // Additional fields
  if (location.website) {
    schema.url = location.website;
  }
  
  if (location.image) {
    schema.image = location.image.startsWith("http") 
      ? location.image 
      : getAbsoluteUrl(location.image);
  }
  
  if (location.description) {
    schema.description = location.description;
  }
  
  if (location.phone) {
    schema.telephone = location.phone;
  }
  
  if (location.category) {
    // Map category to schema.org type
    const categoryMap: Record<string, string> = {
      restaurant: "Restaurant",
      bakery: "Bakery",
      supermarket: "GroceryStore",
      barber: "HairSalon",
      mosque: "PlaceOfWorship",
      travel_agency: "TravelAgency",
      butcher: "ButcherShop",
      fast_food: "FastFoodRestaurant",
    };
    
    const cuisineType = categoryMap[location.category];
    if (cuisineType === "Restaurant" || cuisineType === "FastFoodRestaurant") {
      schema.servesCuisine = "Turkish";
    }
  }
  
  return schema;
}

