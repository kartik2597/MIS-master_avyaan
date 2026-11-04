// Single source of truth for where the session lives in the browser.
// Both api-client.ts and authStore.ts use this, so the keys and the
// "remember me" rules can never drift apart.

export const TOKEN_STORAGE_KEY = "mis_master_auth_token";
export const USER_STORAGE_KEY = "mis_master_auth_user";
export const REFRESH_STORAGE_KEY = "mis_master_auth_refresh";

function isBrowser() {
  return typeof window !== "undefined";
}

export function readStored(key: string): string | null {
  if (!isBrowser()) return null;
  return window.localStorage.getItem(key) ?? window.sessionStorage.getItem(key);
}

export function getStoredToken(): string | null {
  return readStored(TOKEN_STORAGE_KEY);
}

export function getStoredRefreshToken(): string | null {
  return readStored(REFRESH_STORAGE_KEY);
}

export function clearStoredAuth() {
  if (!isBrowser()) return;
  [window.localStorage, window.sessionStorage].forEach((storage) => {
    storage.removeItem(TOKEN_STORAGE_KEY);
    storage.removeItem(USER_STORAGE_KEY);
    storage.removeItem(REFRESH_STORAGE_KEY);
  });
}

function pickStorages(remember: boolean) {
  return {
    target: remember ? window.localStorage : window.sessionStorage,
    other: remember ? window.sessionStorage : window.localStorage,
  };
}

// Saves the value in the chosen storage and removes it from the other one, so a
// stale copy can never be picked up first (reads prefer localStorage).
export function saveStored(key: string, value: string, remember: boolean) {
  if (!isBrowser()) return;
  const { target, other } = pickStorages(remember);
  target.setItem(key, value);
  other.removeItem(key);
}

export function saveToken(token: string, remember: boolean) {
  saveStored(TOKEN_STORAGE_KEY, token, remember);
}

export function saveRefreshToken(token: string, remember: boolean) {
  saveStored(REFRESH_STORAGE_KEY, token, remember);
}

// After a silent renewal, keep the new tokens in the same storage the session
// already uses, so "Remember me" off still means the session ends with the tab.
export function replaceTokens(accessToken: string, refreshToken: string | null | undefined) {
  if (!isBrowser()) return;
  const remember = window.localStorage.getItem(TOKEN_STORAGE_KEY) !== null;
  saveToken(accessToken, remember);
  if (refreshToken) saveRefreshToken(refreshToken, remember);
}

export function saveUser(user: unknown, remember: boolean) {
  saveStored(USER_STORAGE_KEY, JSON.stringify(user), remember);
}
