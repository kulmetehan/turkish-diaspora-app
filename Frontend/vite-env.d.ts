/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;   // e.g. https://turkish-diaspora-app.onrender.com
  readonly VITE_BASE_PATH?: string;      // bv. /turkish-diaspora-app/
  readonly VITE_FRONTEND_URL?: string;  // e.g. https://turkspot.app (for OAuth redirects)
  readonly VITE_SUPABASE_URL: string;
  readonly VITE_SUPABASE_ANON_KEY: string;
  readonly VITE_RECAPTCHA_SITE_KEY?: string;  // Google reCAPTCHA Enterprise v3 site key
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
