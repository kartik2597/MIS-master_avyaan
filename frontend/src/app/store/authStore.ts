import { useEffect, useState, useSyncExternalStore } from "react";
import * as authApi from "@/services/api/auth";
import { UNAUTHORIZED_EVENT } from "@/lib/api-client";
import {
  TOKEN_STORAGE_KEY,
  USER_STORAGE_KEY,
  clearStoredAuth,
  readStored,
  saveRefreshToken,
  saveToken,
  saveUser,
} from "@/lib/auth-storage";

export type Role = "ADMIN" | "MIS" | "MANAGER" | "TL";

export interface AuthUser {
  id: string;
  fullName: string;
  email: string;
  role: Role;
}

const listeners = new Set<() => void>();
let current: AuthUser | null = null;
let token: string | null = null;
let initialized = false;

function emit() {
  listeners.forEach((l) => l());
}

function loadUser(): AuthUser | null {
  try {
    const raw = readStored(USER_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as AuthUser) : null;
  } catch {
    return null;
  }
}

// The API returned 401 (expired or invalid token): drop the in-memory session
// as well, otherwise the UI keeps showing a logged-in user until a refresh.
// MainLayout reacts to `user` becoming null and sends the person to /login
// through the router, so no full page reload is needed here.
function handleUnauthorized() {
  current = null;
  token = null;
  clearStoredAuth();
  emit();
}

function ensureInit() {
  if (!initialized && typeof window !== "undefined") {
    current = loadUser();
    token = readStored(TOKEN_STORAGE_KEY);
    window.addEventListener(UNAUTHORIZED_EVENT, handleUnauthorized);
    initialized = true;
  }
}

export const authStore = {
  subscribe(listener: () => void) {
    listeners.add(listener);
    ensureInit();
    return () => listeners.delete(listener);
  },
  get(): AuthUser | null {
    ensureInit();
    return current;
  },
  getToken(): string | null {
    ensureInit();
    // Read from storage: the api client swaps the token in the background.
    return readStored(TOKEN_STORAGE_KEY) ?? token;
  },
  isAuthenticated(): boolean {
    ensureInit();
    return Boolean(token);
  },
  async login(email: string, password: string, remember: boolean): Promise<AuthUser> {
    const authToken = await authApi.login(email, password);

    // Start from a clean slate, then save the new token in exactly one storage.
    // Without this, an old token left in localStorage would be read first
    // (even when "Remember me" is off) and /auth/me would run with the wrong token.
    clearStoredAuth();
    saveToken(authToken.access_token, remember);
    if (authToken.refresh_token) saveRefreshToken(authToken.refresh_token, remember);
    token = authToken.access_token;

    let profile: Awaited<ReturnType<typeof authApi.getCurrentUser>>;
    try {
      profile = await authApi.getCurrentUser();
    } catch (error) {
      // Do not leave a half-finished session behind if /auth/me fails.
      token = null;
      clearStoredAuth();
      throw error;
    }

    const user: AuthUser = {
      id: profile.id,
      fullName: profile.full_name,
      email: profile.email,
      role: profile.role,
    };
    current = user;
    saveUser(user, remember);
    emit();
    return user;
  },
  logout() {
    current = null;
    token = null;
    clearStoredAuth();
    emit();
  },
};

export function useAuth() {
  const user = useSyncExternalStore(
    authStore.subscribe,
    () => authStore.get(),
    () => null,
  );
  // Hydration safety
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => setHydrated(true), []);
  return { user: hydrated ? user : null, hydrated };
}
