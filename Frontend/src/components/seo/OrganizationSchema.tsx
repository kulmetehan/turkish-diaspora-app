// Frontend/src/components/seo/OrganizationSchema.tsx
// Organization JSON-LD schema component

import { Helmet } from "react-helmet-async";
import { generateOrganizationSchema } from "@/lib/seo/structuredData";

/**
 * Organization schema component voor structured data
 */
export function OrganizationSchema() {
  const schema = generateOrganizationSchema();
  
  return (
    <Helmet>
      <script type="application/ld+json">
        {JSON.stringify(schema, null, 2)}
      </script>
    </Helmet>
  );
}

