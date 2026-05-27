/**
 * LAYERS — Campfire Game Store
 * =============================================
 * Zustand store for Truth-or-Dare. Server is the source of truth — every
 * WS game_event triggers a re-fetch of the full state (kept simple and
 * resilient against schema drift between client and server).
 *
 * STATE:
 *   game: Game | null         — full game state (null if no game in this room)
 *   isLoading                 — initial fetch
 *   isMutating                — start/answer/vote/etc in flight
 *   error                     — last error message
 *
 * ACTIONS:
 *   fetchGame(roomId)         — load current game state for a campfire
 *   startGame(roomId)
 *   submitAnswer(roomId, content)
 *   moveToVoting(roomId)
 *   vote(roomId, answerId)
 *   reveal(roomId)
 *   nextRound(roomId)
 *   endGame(roomId)
 *   clear()                   — reset state when leaving the screen
 *   clearError()
 */

import { create } from "zustand";
import { gameService } from "../services/game";
import { Game } from "../types/game";

interface GameStoreState {
  game: Game | null;
  isLoading: boolean;
  isMutating: boolean;
  error: string | null;

  fetchGame: (roomId: string) => Promise<void>;
  startGame: (roomId: string) => Promise<boolean>;
  submitAnswer: (roomId: string, content: string) => Promise<boolean>;
  moveToVoting: (roomId: string) => Promise<boolean>;
  vote: (roomId: string, answerId: string) => Promise<boolean>;
  reveal: (roomId: string) => Promise<boolean>;
  nextRound: (roomId: string) => Promise<boolean>;
  endGame: (roomId: string) => Promise<boolean>;
  clear: () => void;
  clearError: () => void;
}

function pickError(e: any, fallback: string): string {
  return e?.response?.data?.detail || fallback;
}

export const useGameStore = create<GameStoreState>((set, get) => ({
  game: null,
  isLoading: false,
  isMutating: false,
  error: null,

  fetchGame: async (roomId) => {
    set({ isLoading: true, error: null });
    try {
      const game = await gameService.getGame(roomId);
      set({ game, isLoading: false });
    } catch (e: any) {
      // 404 just means "no game in this room" — not an error to surface
      if (e?.response?.status === 404) {
        set({ game: null, isLoading: false });
      } else {
        set({
          error: pickError(e, "Failed to load game"),
          isLoading: false,
        });
      }
    }
  },

  startGame: async (roomId) => {
    set({ isMutating: true, error: null });
    try {
      const game = await gameService.start(roomId);
      set({ game, isMutating: false });
      return true;
    } catch (e: any) {
      set({ error: pickError(e, "Could not start game"), isMutating: false });
      return false;
    }
  },

  submitAnswer: async (roomId, content) => {
    set({ isMutating: true, error: null });
    try {
      const game = await gameService.submitAnswer(roomId, content);
      set({ game, isMutating: false });
      return true;
    } catch (e: any) {
      set({
        error: pickError(e, "Could not submit answer"),
        isMutating: false,
      });
      return false;
    }
  },

  moveToVoting: async (roomId) => {
    set({ isMutating: true, error: null });
    try {
      const game = await gameService.moveToVoting(roomId);
      set({ game, isMutating: false });
      return true;
    } catch (e: any) {
      set({ error: pickError(e, "Could not open voting"), isMutating: false });
      return false;
    }
  },

  vote: async (roomId, answerId) => {
    set({ isMutating: true, error: null });
    try {
      const game = await gameService.vote(roomId, answerId);
      set({ game, isMutating: false });
      return true;
    } catch (e: any) {
      set({ error: pickError(e, "Could not cast vote"), isMutating: false });
      return false;
    }
  },

  reveal: async (roomId) => {
    set({ isMutating: true, error: null });
    try {
      const game = await gameService.reveal(roomId);
      set({ game, isMutating: false });
      return true;
    } catch (e: any) {
      set({ error: pickError(e, "Could not reveal"), isMutating: false });
      return false;
    }
  },

  nextRound: async (roomId) => {
    set({ isMutating: true, error: null });
    try {
      const game = await gameService.nextRound(roomId);
      set({ game, isMutating: false });
      return true;
    } catch (e: any) {
      set({ error: pickError(e, "Could not advance"), isMutating: false });
      return false;
    }
  },

  endGame: async (roomId) => {
    set({ isMutating: true, error: null });
    try {
      const game = await gameService.end(roomId);
      set({ game, isMutating: false });
      return true;
    } catch (e: any) {
      set({ error: pickError(e, "Could not end game"), isMutating: false });
      return false;
    }
  },

  clear: () =>
    set({
      game: null,
      isLoading: false,
      isMutating: false,
      error: null,
    }),

  clearError: () => set({ error: null }),
}));
