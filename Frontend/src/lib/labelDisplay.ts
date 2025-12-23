/**
 * Helper functions for displaying Söz labels in Turkish.
 */

export function labelDisplayName(label: string): string {
  const labelMap: Record<string, string> = {
    sözü_dinlenir: "Sözü Dinlenir",
    yerinde_tespit: "Yerinde Tespit",
  };
  return labelMap[label] || label;
}


