// ===========================================
// LAYERS API Service
// Axios instance with auth interceptors
// ===========================================

import axios, {
  AxiosError,
  AxiosInstance,
  InternalAxiosRequestConfig,
  AxiosResponse,
} from "axios";
import * as SecureStore from "expo-secure-store";
import { Config } from "../constants/config";

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: Config.API_URL,
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

// Flag to prevent multiple refresh attempts
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: any) => void;
}> = [];

// Process failed queue after token refresh
const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((promise) => {
    if (error) {
      promise.reject(error);
    } else {
      promise.resolve(token!);
    }
  });
  failedQueue = [];
};

// ============================================
// REQUEST INTERCEPTOR
// Adds auth token to every request
// ============================================
api.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    try {
      const token = await SecureStore.getItemAsync("access_token");

      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch (error) {
      console.error("Error getting token:", error);
    }

    // Log request in dev mode
    if (__DEV__) {
      console.log(`🚀 ${config.method?.toUpperCase()} ${config.url}`);
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);

// ============================================
// RESPONSE INTERCEPTOR
// Handles token refresh on 401 errors
// ============================================
api.interceptors.response.use(
  (response: AxiosResponse) => {
    // Log successful response in dev mode
    if (__DEV__) {
      console.log(`✅ ${response.status} ${response.config.url}`);
    }
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    // Log error in dev mode
    if (__DEV__) {
      console.log(`❌ ${error.response?.status} ${originalRequest?.url}`);
      console.log("Error:", error.response?.data);
    }

    // Skip token refresh for auth endpoints - a 401 here means invalid credentials
    const authEndpoints = ['/auth/login', '/auth/register', '/auth/refresh'];
    const isAuthRequest = authEndpoints.some(endpoint =>
      originalRequest.url?.includes(endpoint)
    );

    if (error.response?.status === 401 && !originalRequest._retry && !isAuthRequest) {
      // If already refreshing, queue this request
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`;
            }
            return api(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const refreshToken = await SecureStore.getItemAsync("refresh_token");

        if (!refreshToken) {
          throw new Error("No refresh token");
        }

        // Call refresh endpoint
        const response = await axios.post(`${Config.API_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        });

        const { access_token, refresh_token: newRefreshToken } = response.data;

        // Store new tokens
        await SecureStore.setItemAsync("access_token", access_token);
        if (newRefreshToken) {
          await SecureStore.setItemAsync("refresh_token", newRefreshToken);
        }

        // Process queued requests
        processQueue(null, access_token);

        // Retry original request
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
        }

        return api(originalRequest);
      } catch (refreshError) {
        // Refresh failed - clear tokens and reject queue
        processQueue(refreshError, null);

        await SecureStore.deleteItemAsync("access_token");
        await SecureStore.deleteItemAsync("refresh_token");
        await SecureStore.deleteItemAsync("user");

        // The app should detect this and redirect to login
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  },
);

// ============================================
// HELPER FUNCTIONS
// ============================================

// Parse API error messages
export const getErrorMessage = (error: any): string => {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data;

    // FastAPI validation errors
    if (data?.detail) {
      if (typeof data.detail === "string") {
        return data.detail;
      }
      // Pydantic validation errors
      if (Array.isArray(data.detail)) {
        return data.detail.map((e: any) => e.msg).join(", ");
      }
    }

    // HTTP status messages
    switch (error.response?.status) {
      case 400:
        return "Invalid request. Please check your input.";
      case 401:
        return "Invalid credentials. Please try again.";
      case 403:
        return "You do not have permission to perform this action.";
      case 404:
        return "Resource not found.";
      case 409:
        return "This resource already exists.";
      case 422:
        return "Validation error. Please check your input.";
      case 429:
        return "Too many requests. Please wait and try again.";
      case 500:
        return "Server error. Please try again later.";
      default:
        return "An unexpected error occurred.";
    }
  }

  // Network errors
  if (error.message === "Network Error") {
    return "Unable to connect to server. Please check your internet connection.";
  }

  return error.message || "An unexpected error occurred.";
};

// Check if error is a network error
export const isNetworkError = (error: any): boolean => {
  return !error.response && error.message === "Network Error";
};

// Check if error is an auth error
export const isAuthError = (error: any): boolean => {
  return error.response?.status === 401;
};

export default api;
