import {
  clearStoredAuth,
  getStoredRefreshToken,
  getStoredToken,
  replaceTokens,
} from "@/lib/auth-storage";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
// Listened to by the auth store so the UI drops its in-memory session too.
export const UNAUTHORIZED_EVENT = "auth:unauthorized";

const GENERIC_API_ERROR = "API request failed";

// FastAPI returns `detail` as a string for HTTPException, but as an array of
// { loc, msg, type } objects for validation (422) errors. Turn both into text.
function formatDetail(detail: unknown): string {
  if (typeof detail === "string" && detail.trim()) return detail;

  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) {
          const { loc, msg } = item as { loc?: unknown; msg: unknown };
          const field = Array.isArray(loc)
            ? loc.filter((part) => part !== "body" && part !== "query").join(".")
            : "";
          return field ? `${field}: ${String(msg)}` : String(msg);
        }
        return null;
      })
      .filter((part): part is string => Boolean(part));
    if (parts.length > 0) return parts.join("; ");
  }

  return GENERIC_API_ERROR;
}

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(formatDetail(detail));
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

// Use in the UI instead of hard-coded "Unable to ..." text so people see the
// real reason (e.g. "Insufficient permissions", "email: value is not a valid email").
export function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    return error.message === GENERIC_API_ERROR ? fallback : error.message;
  }
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: BodyInit | Record<string, unknown> | null;
};

// One renewal at a time: if several requests get a 401 together they all wait
// for the same refresh call instead of each spending the refresh token.
let refreshInFlight: Promise<boolean> | null = null;

async function renewSession(): Promise<boolean> {
  const refreshToken = getStoredRefreshToken();
  if (!refreshToken) return false;
  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!response.ok) return false;
    const tokens = (await response.json()) as {
      access_token: string;
      refresh_token?: string | null;
    };
    replaceTokens(tokens.access_token, tokens.refresh_token);
    return true;
  } catch {
    return false;
  }
}

function refreshSession(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = renewSession().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
  retried = false,
): Promise<T> {
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

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
      body: body as BodyInit | null | undefined,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError(0, "Cannot reach the server. Check your connection and try again.");
  }

  if (response.status === 401) {
    // A wrong password on the login form is also a 401; that is not an expired session.
    if (typeof window !== "undefined" && !path.startsWith("/auth/login")) {
      // The access token may just have expired: renew it once and repeat the request.
      if (!retried && (await refreshSession())) {
        return apiRequest<T>(path, options, true);
      }
      clearStoredAuth();
      window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
    }
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
