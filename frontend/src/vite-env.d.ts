/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  /** Dev and test only: serve the API from the typed MSW fixtures. */
  readonly VITE_USE_FIXTURES?: string;
}
