// ============================================================
// src/utils/index.ts - Export all utilities
// ============================================================

export {
  parseError,
  showErrorAlert,
  logError,
  safeAsync,
  ErrorType,
} from "./errorHandler";
export type { AppError } from "./errorHandler";

export { haptics } from "./haptics";

export {
  required,
  isEmail,
  minLength,
  maxLength,
  hasUppercase,
  hasNumber,
  hasSpecialChar,
  isUsername,
  matchesField,
  validateForm,
  hasErrors,
  getPasswordStrength,
} from "./validation";
export type { PasswordStrength } from "./validation";
