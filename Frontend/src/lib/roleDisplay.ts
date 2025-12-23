/**
 * Helper functions for displaying user roles in Turkish.
 */

export function roleDisplayName(role: string | null | undefined): string {
  const roleMap: Record<string, string> = {
    yeni_gelen: "Yeni Gelen",
    mahalleli: "Mahalleli",
    anlatıcı: "Anlatıcı",
    ses_veren: "Ses Veren",
    sözü_dinlenir: "Sözü Dinlenir",
    yerinde_tespit: "Yerinde Tespit",
    sessiz_güç: "Sessiz Güç",
  };
  return role ? roleMap[role] || role : "";
}


