import api, { getErrorMessage } from "./api";
import { User, AuthTokens } from "../types";

// ============================================
// REQUEST/RESPONSE TYPES
// ============================================

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
}

export interface AuthResponse {
  user: User;
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface PasswordResetRequest {
  email: string;
}

export interface PasswordResetConfirm {
  token: string;
  new_password: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

// ============================================
// AUTH SERVICE
// ============================================

export const authService = {
  /**
   * Login user with email and password
   */
  login: async (data: LoginRequest): Promise<AuthResponse> => {
    const response = await api.post<AuthResponse>("/auth/login", data);
    return response.data;
  },

  /**
   * Register new user
   */
  register: async (data: RegisterRequest): Promise<AuthResponse> => {
    const response = await api.post<AuthResponse>("/auth/register", data);
    return response.data;
  },

  /**
   * Logout user (invalidate token on server)
   */
  logout: async (): Promise<void> => {
    try {
      await api.post("/auth/logout");
    } catch (error) {
      // Even if server logout fails, we still clear local tokens
      console.log("Server logout failed, clearing local tokens");
    }
  },

  /**
   * Get current user profile
   */
  getProfile: async (): Promise<User> => {
    const response = await api.get<User>("/auth/me");
    return response.data;
  },

  /**
   * Update user profile
   */
  updateProfile: async (data: Partial<User>): Promise<User> => {
    const response = await api.put<User>("/auth/me", data);
    return response.data;
  },

  /**
   * Request password reset email
   */
  requestPasswordReset: async (email: string): Promise<{ message: string }> => {
    const response = await api.post<{ message: string }>(
      "/auth/password-reset/request",
      { email },
    );
    return response.data;
  },

  /**
   * Confirm password reset with token
   */
  confirmPasswordReset: async (
    token: string,
    newPassword: string,
  ): Promise<{ message: string }> => {
    const response = await api.post<{ message: string }>(
      "/auth/password-reset/confirm",
      { token, new_password: newPassword },
    );
    return response.data;
  },

  /**
   * Change password (when logged in)
   */
  changePassword: async (
    data: ChangePasswordRequest,
  ): Promise<{ message: string }> => {
    const response = await api.post<{ message: string }>(
      "/auth/change-password",
      data,
    );
    return response.data;
  },

  /**
   * Check if email is available
   */
  checkEmail: async (email: string): Promise<{ available: boolean }> => {
    const response = await api.get<{ available: boolean }>(
      `/auth/check-email/${encodeURIComponent(email)}`,
    );
    return response.data;
  },

  /**
   * Check if username is available
   */
  checkUsername: async (username: string): Promise<{ available: boolean }> => {
    const response = await api.get<{ available: boolean }>(
      `/auth/check-username/${encodeURIComponent(username)}`,
    );
    return response.data;
  },

  /**
   * Refresh access token
   */
  refreshToken: async (refreshToken: string): Promise<AuthTokens> => {
    const response = await api.post<AuthTokens>("/auth/refresh", {
      refresh_token: refreshToken,
    });
    return response.data;
  },

  /**
   * Deactivate account
   */
  deactivateAccount: async (): Promise<void> => {
    await api.delete("/auth/me");
  },
};

// Export helper for getting error messages
export { getErrorMessage };
