/**
 * LAYERS - Global Error Handler
 * Centralized error handling for the entire app
 *
 * WHY: Production apps MUST handle errors gracefully.
 * Users should never see raw error messages or white screens.
 */

import { Alert } from "react-native";

// ============================================================
// ERROR TYPES - Categorize errors for better handling
// ============================================================

export enum ErrorType {
  NETWORK = "NETWORK", // No internet, timeout
  AUTH = "AUTH", // Token expired, unauthorized
  VALIDATION = "VALIDATION", // Bad input from user
  SERVER = "SERVER", // 500 errors from backend
  LOCATION = "LOCATION", // GPS denied, unavailable
  STORAGE = "STORAGE", // AsyncStorage failures
  UNKNOWN = "UNKNOWN", // Catch-all
}

export interface AppError {
  type: ErrorType;
  message: string; // User-friendly message
  technicalMessage?: string; // For debugging (never show to user)
  statusCode?: number;
  retryable: boolean; // Can user retry this action?
}

// ============================================================
// ERROR PARSER - Convert raw errors to AppError
// ============================================================

export function parseError(error: any): AppError {
  // Axios/Network errors
  if (error?.response) {
    const status = error.response.status;
    const serverMsg =
      error.response.data?.detail || error.response.data?.message;

    if (status === 401) {
      return {
        type: ErrorType.AUTH,
        message: "Session expired. Please log in again.",
        technicalMessage: serverMsg,
        statusCode: status,
        retryable: false,
      };
    }

    if (status === 403) {
      return {
        type: ErrorType.AUTH,
        message: "You don't have permission for this action.",
        technicalMessage: serverMsg,
        statusCode: status,
        retryable: false,
      };
    }

    if (status === 422) {
      return {
        type: ErrorType.VALIDATION,
        message: serverMsg || "Please check your input and try again.",
        technicalMessage: JSON.stringify(error.response.data),
        statusCode: status,
        retryable: true,
      };
    }

    if (status === 429) {
      return {
        type: ErrorType.SERVER,
        message: "Too many requests. Please wait a moment.",
        technicalMessage: "Rate limited",
        statusCode: status,
        retryable: true,
      };
    }

    if (status >= 500) {
      return {
        type: ErrorType.SERVER,
        message: "Something went wrong on our end. Please try again.",
        technicalMessage: serverMsg,
        statusCode: status,
        retryable: true,
      };
    }

    return {
      type: ErrorType.SERVER,
      message: serverMsg || "Something went wrong.",
      technicalMessage: `Status ${status}: ${serverMsg}`,
      statusCode: status,
      retryable: true,
    };
  }

  // No response = network error
  if (error?.request || error?.message?.includes("Network")) {
    return {
      type: ErrorType.NETWORK,
      message: "No internet connection. Check your network and try again.",
      technicalMessage: error.message,
      retryable: true,
    };
  }

  // Timeout
  if (error?.code === "ECONNABORTED" || error?.message?.includes("timeout")) {
    return {
      type: ErrorType.NETWORK,
      message: "Request timed out. Please try again.",
      technicalMessage: error.message,
      retryable: true,
    };
  }

  // Location errors
  if (
    error?.message?.includes("Location") ||
    error?.message?.includes("permission")
  ) {
    return {
      type: ErrorType.LOCATION,
      message: "Location access needed. Please enable GPS in settings.",
      technicalMessage: error.message,
      retryable: true,
    };
  }

  // Default unknown error
  return {
    type: ErrorType.UNKNOWN,
    message: "Something unexpected happened. Please try again.",
    technicalMessage: error?.message || String(error),
    retryable: true,
  };
}

// ============================================================
// USER-FACING ERROR DISPLAY
// ============================================================

export function showErrorAlert(error: AppError, onRetry?: () => void): void {
  const buttons: any[] = [{ text: "OK", style: "cancel" }];

  if (error.retryable && onRetry) {
    buttons.push({ text: "Retry", onPress: onRetry });
  }

  Alert.alert("Oops!", error.message, buttons);
}

// ============================================================
// ERROR LOGGER - For debugging in development
// ============================================================

export function logError(context: string, error: any): void {
  if (__DEV__) {
    console.error(`[LAYERS ERROR] ${context}:`, {
      message: error?.message,
      status: error?.response?.status,
      data: error?.response?.data,
      stack: error?.stack?.slice(0, 200),
    });
  }
  // TODO: In production, send to error tracking service (Sentry, Bugsnag)
  // Sentry.captureException(error, { extra: { context } });
}

// ============================================================
// SAFE ASYNC WRAPPER - Wrap any async function with error handling
// ============================================================

export async function safeAsync<T>(
  fn: () => Promise<T>,
  context: string,
): Promise<{ data: T | null; error: AppError | null }> {
  try {
    const data = await fn();
    return { data, error: null };
  } catch (err) {
    const appError = parseError(err);
    logError(context, err);
    return { data: null, error: appError };
  }
}
