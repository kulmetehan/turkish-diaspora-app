/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;   // bv. https://tda-api.onrender.com
  readonly VITE_BASE_PATH?: string;      // bv. /turkish-diaspora-app/
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
