// Frontend/src/components/seo/WebsiteSchema.tsx
// Website JSON-LD schema component

import { Helmet } from "react-helmet-async";
import { generateWebsiteSchema } from "@/lib/seo/structuredData";

/**
 * Website schema component voor structured data
 */
export function WebsiteSchema() {
  const schema = generateWebsiteSchema();
  
  return (
    <Helmet>
      <script type="application/ld+json">
        {JSON.stringify(schema, null, 2)}
      </script>
    </Helmet>
  );
}








