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

/** Change the signed-in user's own password. */
export function changePassword(currentPassword: string, newPassword: string) {
  return apiRequest<void>("/auth/change-password", {
    method: "POST",
    body: { current_password: currentPassword, new_password: newPassword },
  });
}

/** Every user. Admin only. */
export function listUsers() {
  return apiRequest<User[]>("/auth/users");
}

/** Link a user to an employee by Employee ID, or clear the link with null. Admin only. */
export function setUserEmployee(userId: string, empId: string | null) {
  return apiRequest<User>(`/auth/users/${userId}/employee`, {
    method: "PUT",
    body: { emp_id: empId },
  });
}

export function createUser(payload: UserCreatePayload) {
  return apiRequest<User>("/auth/create-user", {
    method: "POST",
    body: payload,
  });
}
