/**
 * Backend URL config.
 * In the desktop (Electron) build this is always localhost:8001.
 * In mobile/web builds it comes from EXPO_PUBLIC_BACKEND_URL.
 */
export const BACKEND_URL: string =
  process.env.EXPO_PUBLIC_BACKEND_URL || 'http://localhost:8001';
