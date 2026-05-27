/**
 * LAYERS — Campfire Game Service
 * ===============================================
 * REST helpers for Truth-or-Dare.
 * Object-literal pattern (matches authService/chatService).
 */

import api from "./api";
import { Game, AnswerSubmitRequest, VoteCastRequest } from "../types/game";

const base = (roomId: string) => `/chat/campfires/${roomId}/game`;

export const gameService = {
  getGame: async (roomId: string): Promise<Game> => {
    const response = await api.get<Game>(base(roomId));
    return response.data;
  },

  start: async (roomId: string): Promise<Game> => {
    const response = await api.post<Game>(`${base(roomId)}/start`);
    return response.data;
  },

  submitAnswer: async (roomId: string, content: string): Promise<Game> => {
    const body: AnswerSubmitRequest = { content };
    const response = await api.post<Game>(`${base(roomId)}/answer`, body);
    return response.data;
  },

  moveToVoting: async (roomId: string): Promise<Game> => {
    const response = await api.post<Game>(`${base(roomId)}/move-to-voting`);
    return response.data;
  },

  vote: async (roomId: string, answerId: string): Promise<Game> => {
    const body: VoteCastRequest = { answer_id: answerId };
    const response = await api.post<Game>(`${base(roomId)}/vote`, body);
    return response.data;
  },

  reveal: async (roomId: string): Promise<Game> => {
    const response = await api.post<Game>(`${base(roomId)}/reveal`);
    return response.data;
  },

  nextRound: async (roomId: string): Promise<Game> => {
    const response = await api.post<Game>(`${base(roomId)}/next-round`);
    return response.data;
  },

  end: async (roomId: string): Promise<Game> => {
    const response = await api.post<Game>(`${base(roomId)}/end`);
    return response.data;
  },
};
