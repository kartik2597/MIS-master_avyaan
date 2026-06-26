import { apiRequest } from "@/lib/api-client";
import type { Token, User, UserCreatePayload } from "./types";

export function login(email: string, password: string) {
  return apiRequest<Token>("/auth/login", {
    method: "POST",
    body: { email, password },
  });
}

export function getCurrentUser() {
  return apiRequest<User>("/auth/me");
}

export function createUser(payload: UserCreatePayload) {
  return apiRequest<User>("/auth/create-user", {
    method: "POST",
    body: payload,
  });
}
