// Frontend/src/components/seo/LocationSchema.tsx
// LocalBusiness JSON-LD schema component voor locaties

import { Helmet } from "react-helmet-async";
import { generateLocationSchema, type LocalBusinessSchema } from "@/lib/seo/structuredData";

export interface LocationSchemaProps {
  location: {
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
  };
}

/**
 * Location schema component voor structured data
 * Alleen renderen wanneer location data beschikbaar is
 */
export function LocationSchema({ location }: LocationSchemaProps) {
  if (!location || !location.name) {
    return null;
  }
  
  const schema: LocalBusinessSchema = generateLocationSchema(location);
  
  return (
    <Helmet>
      <script type="application/ld+json">
        {JSON.stringify(schema, null, 2)}
      </script>
    </Helmet>
  );
}






