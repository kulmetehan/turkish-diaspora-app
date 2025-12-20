/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;   // e.g. https://turkish-diaspora-app.onrender.com
  readonly VITE_BASE_PATH?: string;      // bv. /turkish-diaspora-app/
  readonly VITE_SUPABASE_URL: string;
  readonly VITE_SUPABASE_ANON_KEY: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
