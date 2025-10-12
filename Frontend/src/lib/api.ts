export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string;

if (!API_BASE_URL) {
  // Valt op tijdens dev als je .env mist
  // (console.warn is genoeg; we willen geen crash)
  console.warn('VITE_API_BASE_URL is not set in your environment files.');
}

export async function getHealth(): Promise<{ status: string } | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/health`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch {
    return null;
  }
}
