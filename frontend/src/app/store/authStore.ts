import { useEffect, useState, useSyncExternalStore } from "react";
import * as authApi from "@/services/api/auth";

export type Role = "ADMIN" | "MIS" | "MANAGER";

export interface AuthUser {
  id: string;
  fullName: string;
  email: string;
  role: Role;
}

const USER_STORAGE_KEY = "mis_master_auth_user";
const TOKEN_STORAGE_KEY = "mis_master_auth_token";

const listeners = new Set<() => void>();
let current: AuthUser | null = null;
let token: string | null = null;
let initialized = false;

function emit() {
  listeners.forEach((l) => l());
}

function readStorage(key: string): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(key) ?? window.sessionStorage.getItem(key);
}

function loadUser(): AuthUser | null {
  try {
    const raw = readStorage(USER_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as AuthUser) : null;
  } catch {
    return null;
  }
}

function ensureInit() {
  if (!initialized && typeof window !== "undefined") {
    current = loadUser();
    token = readStorage(TOKEN_STORAGE_KEY);
    initialized = true;
  }
}

function persistSession(user: AuthUser, accessToken: string, remember: boolean) {
  if (typeof window === "undefined") return;
  const storage = remember ? window.localStorage : window.sessionStorage;
  const otherStorage = remember ? window.sessionStorage : window.localStorage;

  storage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
  storage.setItem(TOKEN_STORAGE_KEY, accessToken);
  otherStorage.removeItem(USER_STORAGE_KEY);
  otherStorage.removeItem(TOKEN_STORAGE_KEY);
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
    return token;
  },
  isAuthenticated(): boolean {
    ensureInit();
    return Boolean(token);
  },
 async login(email: string, password: string, remember: boolean): Promise<AuthUser> {
  const authToken = await authApi.login(email, password);
  token = authToken.access_token;

  // Token save karo before calling /auth/me
  const storage = remember ? window.localStorage : window.sessionStorage;
  storage.setItem(TOKEN_STORAGE_KEY, token);

  const profile = await authApi.getCurrentUser();

  const user: AuthUser = {
    id: profile.id,
    fullName: profile.full_name,
    email: profile.email,
    role: profile.role,
  };
    current = user;
    persistSession(user, token, remember);
    emit();
    return user;
  },
  logout() {
    current = null;
    token = null;
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(USER_STORAGE_KEY);
      window.localStorage.removeItem(TOKEN_STORAGE_KEY);
      window.sessionStorage.removeItem(USER_STORAGE_KEY);
      window.sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    }
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
