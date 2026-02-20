// LAYERS Color System
// Light Layer = Daytime, healing, calm
// Shadow Layer = Nighttime, mysterious, thrilling

export const Colors = {
  // Light Layer (Default)
  light: {
    primary: "#6366F1", // Indigo - main brand color
    secondary: "#EC4899", // Pink - accent
    background: "#F8FAFC", // Light gray background
    surface: "#FFFFFF", // White cards/surfaces
    text: "#1E293B", // Dark text
    textSecondary: "#64748B", // Gray text
    border: "#E2E8F0", // Light borders
    success: "#10B981", // Green
    error: "#EF4444", // Red
    warning: "#F59E0B", // Orange
  },

  // Shadow Layer (Night mode)
  shadow: {
    primary: "#8B5CF6", // Purple - mysterious
    secondary: "#F43F5E", // Rose - danger/excitement
    background: "#0F172A", // Very dark blue
    surface: "#1E293B", // Dark cards
    text: "#F8FAFC", // Light text
    textSecondary: "#94A3B8", // Muted text
    border: "#334155", // Dark borders
    success: "#10B981",
    error: "#EF4444",
    warning: "#F59E0B",
  },
};

export type ColorScheme = typeof Colors.light;
export type Layer = "light" | "shadow";
