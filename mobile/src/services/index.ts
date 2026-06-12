export {
  default as api,
  getErrorMessage,
  isNetworkError,
  isAuthError,
} from "./api";

export { authService } from "./auth";
export { inboxService } from "./inbox";
export { notificationService } from "./notifications";
export { artifactService } from "./artifacts";
export { exploreService } from "./explore";
export { profileService } from "./profile";
export { connectionService } from "./connections";
export { timeCapsuleService, paperPlaneService } from "./planes_capsules";
export { chatService, WebSocketClient, buildWSUrl } from "./chat";
export { socialSparkService } from "./social_spark";
export { gameService } from "./game";
export { gamificationService } from "./gamification";

export type {
  LoginRequest,
  RegisterRequest,
  AuthResponse,
  PasswordResetRequest,
  ChangePasswordRequest,
} from "./auth";

export type { UpdateProfileRequest, ProfileStats } from "./profile";
