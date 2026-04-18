/**
 * API key for desktop (Electron/same-machine) use.
 * Set EXPO_PUBLIC_API_KEY in your .env file.
 * The key is read at runtime and attached to every request via utils/api.ts.
 */
export function getApiKey(): string {
  return process.env.EXPO_PUBLIC_API_KEY ?? '';
}
