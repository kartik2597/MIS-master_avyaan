const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const TOKEN_STORAGE_KEY = "mis_master_auth_token";
const USER_STORAGE_KEY = "mis_master_auth_user";

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : "API request failed");
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: BodyInit | Record<string, unknown> | null;
};

function getStoredToken() {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_STORAGE_KEY) ?? window.sessionStorage.getItem(TOKEN_STORAGE_KEY);
}

function clearStoredAuth() {
  if (typeof window === "undefined") return;
  [window.localStorage, window.sessionStorage].forEach((storage) => {
    storage.removeItem(TOKEN_STORAGE_KEY);
    storage.removeItem(USER_STORAGE_KEY);
  });
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const token = getStoredToken();
  let body = options.body;

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  if (body && !(body instanceof FormData) && typeof body !== "string") {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(body);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    body: body as BodyInit | null | undefined,
  });

  if (response.status === 401) {
    clearStoredAuth();
  }

  if (!response.ok) {
    let detail: unknown = response.statusText;
    try {
      const payload = await response.json();
      detail = payload.detail ?? payload;
    } catch {
      detail = response.statusText;
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}
