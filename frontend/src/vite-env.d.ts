/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly RUN_REAL_API?: string;
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_API_ACCESS_TOKEN?: string;
  readonly VITE_SUPABASE_URL?: string;
  readonly VITE_SUPABASE_ANON_KEY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
