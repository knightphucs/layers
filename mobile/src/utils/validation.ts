/**
 * LAYERS - Form Validation Utilities
 * Centralized validation rules used across all forms
 *
 * WHY: Consistent validation = better UX.
 * Same rules on mobile AND backend = fewer bugs.
 *
 * USAGE:
 *   const errors = validateForm({
 *     email: [required('Email'), isEmail],
 *     password: [required('Password'), minLength(8), hasUppercase, hasNumber],
 *   }, { email: 'test@', password: '123' });
 *   // => { email: 'Enter a valid email', password: 'Must be at least 8 characters' }
 */

// ============================================================
// VALIDATION RULES - Each returns error string or null
// ============================================================

type Validator = (value: any) => string | null;

/** Field is required */
export const required =
  (fieldName: string): Validator =>
  (value) => {
    if (!value || (typeof value === "string" && !value.trim())) {
      return `${fieldName} is required`;
    }
    return null;
  };

/** Valid email format */
export const isEmail: Validator = (value) => {
  const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (value && !regex.test(value)) {
    return "Enter a valid email address";
  }
  return null;
};

/** Minimum length */
export const minLength =
  (min: number): Validator =>
  (value) => {
    if (value && value.length < min) {
      return `Must be at least ${min} characters`;
    }
    return null;
  };

/** Maximum length */
export const maxLength =
  (max: number): Validator =>
  (value) => {
    if (value && value.length > max) {
      return `Must be no more than ${max} characters`;
    }
    return null;
  };

/** Contains uppercase letter */
export const hasUppercase: Validator = (value) => {
  if (value && !/[A-Z]/.test(value)) {
    return "Must contain at least one uppercase letter";
  }
  return null;
};

/** Contains number */
export const hasNumber: Validator = (value) => {
  if (value && !/\d/.test(value)) {
    return "Must contain at least one number";
  }
  return null;
};

/** Contains special character */
export const hasSpecialChar: Validator = (value) => {
  if (value && !/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(value)) {
    return "Must contain at least one special character";
  }
  return null;
};

/** Username format (alphanumeric, underscores, 3-20 chars) */
export const isUsername: Validator = (value) => {
  if (value && !/^[a-zA-Z0-9_]{3,20}$/.test(value)) {
    return "Username: 3-20 characters, letters, numbers, underscores only";
  }
  return null;
};

/** Password matches confirmation */
export const matchesField =
  (fieldName: string, matchValue: string): Validator =>
  (value) => {
    if (value && value !== matchValue) {
      return `Must match ${fieldName}`;
    }
    return null;
  };

// ============================================================
// FORM VALIDATOR - Run all rules at once
// ============================================================

type ValidationRules = Record<string, Validator[]>;
type ValidationErrors = Record<string, string>;

/**
 * Validate entire form at once
 * Returns object of field -> error message (only for failed fields)
 */
export function validateForm(
  rules: ValidationRules,
  values: Record<string, any>,
): ValidationErrors {
  const errors: ValidationErrors = {};

  for (const [field, validators] of Object.entries(rules)) {
    for (const validator of validators) {
      const error = validator(values[field]);
      if (error) {
        errors[field] = error;
        break; // Stop at first error per field
      }
    }
  }

  return errors;
}

/**
 * Check if form has any errors
 */
export function hasErrors(errors: ValidationErrors): boolean {
  return Object.keys(errors).length > 0;
}

// ============================================================
// PASSWORD STRENGTH CALCULATOR
// ============================================================

export type PasswordStrength = "weak" | "fair" | "good" | "strong";

export function getPasswordStrength(password: string): {
  strength: PasswordStrength;
  score: number; // 0-4
  color: string;
  label: string;
} {
  let score = 0;
  if (password.length >= 8) score++;
  if (password.length >= 12) score++;
  if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score++;
  if (/\d/.test(password)) score++;
  if (/[^A-Za-z0-9]/.test(password)) score++;

  if (score <= 1)
    return { strength: "weak", score: 1, color: "#EF4444", label: "Weak" };
  if (score <= 2)
    return { strength: "fair", score: 2, color: "#F59E0B", label: "Fair" };
  if (score <= 3)
    return { strength: "good", score: 3, color: "#3B82F6", label: "Good" };
  return { strength: "strong", score: 4, color: "#10B981", label: "Strong" };
}
