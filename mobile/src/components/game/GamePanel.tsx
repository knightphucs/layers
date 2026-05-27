/**
 * LAYERS — GamePanel Component
 * =============================================
 * The orchestrator. Reads game state from useGameStore and renders
 * the appropriate phase UI:
 *
 *   NO GAME       → "Start Truth or Dare 🔥" button (for campfire members)
 *   ANSWERING     → QuestionCard + answer input (or "waiting…" if submitted)
 *                   + "Move to voting" (starter only, ≥2 answers)
 *   VOTING        → list of anonymous answers, tap to vote (not own)
 *                   + "Reveal" (starter only)
 *   REVEALED      → QuestionCard + winner reveal + answers w/ authors
 *                   + "Next round" / "End game" (starter only)
 *   COMPLETED     → "Game ended" + final state snapshot
 *
 * Drop into CampfireScreen between MembersList and MessageList, or as its
 * own collapsible drawer.
 */

import React, { useEffect, useState, useCallback } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  TextInput,
  StyleSheet,
  ActivityIndicator,
  ScrollView,
} from "react-native";
import { Colors } from "../../constants/colors";
import { useAuthStore } from "../../store/authStore";
import { useGameStore } from "../../store/gameStore";
import { GameAnswer, GameRound } from "../../types/game";
import { haptics } from "../../utils/haptics";
import QuestionCard from "./QuestionCard";

const ANSWER_MAX = 280;

// ============================================================
// SUB-COMPONENT — ANSWER PHASE
// ============================================================

function AnswerPhase({
  roomId,
  round,
  myAnswerSubmitted,
  isStarter,
  isMutating,
}: {
  roomId: string;
  round: GameRound;
  myAnswerSubmitted: boolean;
  isStarter: boolean;
  isMutating: boolean;
}) {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];
  const submitAnswer = useGameStore((s) => s.submitAnswer);
  const moveToVoting = useGameStore((s) => s.moveToVoting);

  const [text, setText] = useState("");

  const handleSubmit = useCallback(async () => {
    const trimmed = text.trim();
    if (!trimmed) return;
    haptics.light();
    const ok = await submitAnswer(roomId, trimmed);
    if (ok) setText("");
  }, [text, roomId, submitAnswer]);

  const answerCount = round.answers.length;
  const canMoveToVoting = isStarter && answerCount >= 2;

  return (
    <View>
      <Text style={[styles.subtle, { color: colors.textSecondary }]}>
        {answerCount} {answerCount === 1 ? "answer" : "answers"} so far
      </Text>

      {!myAnswerSubmitted ? (
        <View style={styles.inputRow}>
          <TextInput
            value={text}
            onChangeText={(t) => setText(t.slice(0, ANSWER_MAX))}
            placeholder="Your answer…"
            placeholderTextColor={colors.textSecondary}
            multiline
            maxLength={ANSWER_MAX}
            style={[
              styles.input,
              {
                backgroundColor: colors.background,
                borderColor: colors.border,
                color: colors.text,
              },
            ]}
          />
          <TouchableOpacity
            onPress={handleSubmit}
            disabled={!text.trim() || isMutating}
            style={[
              styles.submitBtn,
              {
                backgroundColor: text.trim() ? colors.primary : colors.border,
              },
            ]}
            activeOpacity={0.7}
          >
            {isMutating ? (
              <ActivityIndicator size="small" color="#fff" />
            ) : (
              <Text style={styles.submitText}>Send</Text>
            )}
          </TouchableOpacity>
        </View>
      ) : (
        <View style={[styles.statusBox, { borderColor: colors.border }]}>
          <Text style={[styles.statusText, { color: colors.text }]}>
            ✓ Your answer is in. Waiting for others…
          </Text>
        </View>
      )}

      {isStarter && (
        <TouchableOpacity
          onPress={() => {
            haptics.impact();
            moveToVoting(roomId);
          }}
          disabled={!canMoveToVoting || isMutating}
          style={[
            styles.advanceBtn,
            {
              backgroundColor: canMoveToVoting ? "#F59E0B" : colors.border,
            },
          ]}
          activeOpacity={0.7}
        >
          <Text style={styles.advanceText}>
            {canMoveToVoting
              ? "🗳️ Open voting"
              : `Need ${Math.max(0, 2 - answerCount)} more answer${
                  2 - answerCount === 1 ? "" : "s"
                }`}
          </Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

// ============================================================
// SUB-COMPONENT — VOTING PHASE
// ============================================================

function VotingPhase({
  roomId,
  round,
  myVoteCast,
  isStarter,
  isMutating,
}: {
  roomId: string;
  round: GameRound;
  myVoteCast: boolean;
  isStarter: boolean;
  isMutating: boolean;
}) {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];
  const vote = useGameStore((s) => s.vote);
  const reveal = useGameStore((s) => s.reveal);

  const handleVote = useCallback(
    async (answerId: string) => {
      haptics.light();
      await vote(roomId, answerId);
    },
    [roomId, vote],
  );

  return (
    <View>
      <Text style={[styles.subtle, { color: colors.textSecondary }]}>
        {myVoteCast
          ? "Your vote is in — waiting for reveal"
          : "Tap your favorite answer (not your own)"}
      </Text>

      {round.answers.map((answer) => (
        <AnswerCard
          key={answer.id}
          answer={answer}
          canVote={!answer.is_mine && !myVoteCast && !isMutating}
          onVote={() => handleVote(answer.id)}
        />
      ))}

      {isStarter && (
        <TouchableOpacity
          onPress={() => {
            haptics.impact();
            reveal(roomId);
          }}
          disabled={isMutating}
          style={[styles.advanceBtn, { backgroundColor: "#10B981" }]}
          activeOpacity={0.7}
        >
          <Text style={styles.advanceText}>🎉 Reveal the round</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

// ============================================================
// SUB-COMPONENT — REVEAL PHASE
// ============================================================

function RevealPhase({
  roomId,
  round,
  isStarter,
  isMutating,
}: {
  roomId: string;
  round: GameRound;
  isStarter: boolean;
  isMutating: boolean;
}) {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];
  const nextRound = useGameStore((s) => s.nextRound);
  const endGame = useGameStore((s) => s.endGame);

  const winnerName = round.winner_username || "No one";

  return (
    <View>
      <View
        style={[
          styles.winnerCard,
          { backgroundColor: colors.surface, borderColor: "#10B981" },
        ]}
      >
        <Text style={styles.winnerEmoji}>👑</Text>
        <Text style={[styles.winnerLabel, { color: colors.textSecondary }]}>
          Round winner
        </Text>
        <Text style={[styles.winnerName, { color: colors.text }]}>
          {winnerName}
        </Text>
      </View>

      <Text style={[styles.subtle, { color: colors.textSecondary }]}>
        All answers ({round.answers.length}):
      </Text>

      {[...round.answers]
        .sort((a, b) => b.vote_count - a.vote_count)
        .map((answer) => (
          <AnswerCard key={answer.id} answer={answer} revealed />
        ))}

      {isStarter && (
        <View style={styles.endRow}>
          <TouchableOpacity
            onPress={() => {
              haptics.light();
              nextRound(roomId);
            }}
            disabled={isMutating}
            style={[
              styles.advanceBtn,
              { backgroundColor: colors.primary, flex: 1 },
            ]}
            activeOpacity={0.7}
          >
            <Text style={styles.advanceText}>➡️ Next round</Text>
          </TouchableOpacity>
          <TouchableOpacity
            onPress={() => {
              haptics.impact();
              endGame(roomId);
            }}
            disabled={isMutating}
            style={[
              styles.advanceBtn,
              { backgroundColor: "#EF4444" + "20", flex: 1 },
            ]}
            activeOpacity={0.7}
          >
            <Text style={[styles.advanceText, { color: "#EF4444" }]}>
              🏁 End game
            </Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
}

// ============================================================
// ANSWER CARD (used in voting + reveal)
// ============================================================

interface AnswerCardProps {
  answer: GameAnswer;
  canVote?: boolean;
  revealed?: boolean;
  onVote?: () => void;
}

const AnswerCard: React.FC<AnswerCardProps> = ({
  answer,
  canVote,
  revealed,
  onVote,
}) => {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  const body = (
    <View
      style={[
        styles.answerCard,
        {
          backgroundColor: colors.surface,
          borderColor: answer.is_mine ? colors.primary : colors.border,
        },
      ]}
    >
      <Text style={[styles.answerContent, { color: colors.text }]}>
        {answer.content}
      </Text>
      <View style={styles.answerMetaRow}>
        {revealed ? (
          <Text style={[styles.answerAuthor, { color: colors.textSecondary }]}>
            — {answer.username || "Anonymous"}
            {answer.is_mine ? " (you)" : ""}
          </Text>
        ) : (
          <Text style={[styles.answerAuthor, { color: colors.textSecondary }]}>
            {answer.is_mine ? "Your answer" : "Anonymous"}
          </Text>
        )}
        {revealed && answer.vote_count > 0 && (
          <Text style={[styles.voteCount, { color: colors.primary }]}>
            {answer.vote_count} {answer.vote_count === 1 ? "vote" : "votes"}
          </Text>
        )}
      </View>
    </View>
  );

  if (!canVote) return body;
  return (
    <TouchableOpacity onPress={onVote} activeOpacity={0.6}>
      {body}
    </TouchableOpacity>
  );
};

// ============================================================
// MAIN PANEL
// ============================================================

interface GamePanelProps {
  roomId: string;
}

export default function GamePanel({ roomId }: GamePanelProps) {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];
  const user = useAuthStore((s) => s.user);

  const game = useGameStore((s) => s.game);
  const isLoading = useGameStore((s) => s.isLoading);
  const isMutating = useGameStore((s) => s.isMutating);
  const error = useGameStore((s) => s.error);
  const fetchGame = useGameStore((s) => s.fetchGame);
  const startGame = useGameStore((s) => s.startGame);
  const clearError = useGameStore((s) => s.clearError);
  const clear = useGameStore((s) => s.clear);

  useEffect(() => {
    fetchGame(roomId);
    return () => clear();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roomId]);

  const isStarter = !!(game && user && game.starter_id === user.id);

  if (isLoading && !game) {
    return (
      <View style={styles.loadingBox}>
        <ActivityIndicator size="small" color={colors.primary} />
      </View>
    );
  }

  // No game → CTA
  if (!game || game.state === "COMPLETED") {
    return (
      <View
        style={[
          styles.ctaBox,
          { backgroundColor: colors.surface, borderColor: colors.border },
        ]}
      >
        {game?.state === "COMPLETED" && (
          <Text style={[styles.subtle, { color: colors.textSecondary }]}>
            Last game ended. Start another?
          </Text>
        )}
        <TouchableOpacity
          onPress={() => {
            haptics.impact();
            startGame(roomId);
          }}
          disabled={isMutating}
          style={[styles.startBtn, { backgroundColor: "#F59E0B" }]}
          activeOpacity={0.7}
        >
          {isMutating ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <Text style={styles.startText}>🔥 Start Truth or Dare</Text>
          )}
        </TouchableOpacity>
        {error && (
          <TouchableOpacity onPress={clearError} style={styles.errorBox}>
            <Text style={styles.errorText}>{error}</Text>
          </TouchableOpacity>
        )}
      </View>
    );
  }

  const round = game.current_round;
  if (!round) {
    return (
      <View style={styles.loadingBox}>
        <ActivityIndicator size="small" color={colors.primary} />
      </View>
    );
  }

  return (
    <ScrollView
      style={[styles.scroll, { backgroundColor: colors.background }]}
      contentContainerStyle={styles.scrollContent}
    >
      <QuestionCard round={round} />

      <View style={styles.body}>
        {round.state === "ANSWERING" && (
          <AnswerPhase
            roomId={roomId}
            round={round}
            myAnswerSubmitted={game.my_answer_submitted}
            isStarter={isStarter}
            isMutating={isMutating}
          />
        )}
        {round.state === "VOTING" && (
          <VotingPhase
            roomId={roomId}
            round={round}
            myVoteCast={game.my_vote_cast}
            isStarter={isStarter}
            isMutating={isMutating}
          />
        )}
        {round.state === "REVEALED" && (
          <RevealPhase
            roomId={roomId}
            round={round}
            isStarter={isStarter}
            isMutating={isMutating}
          />
        )}
      </View>

      {error && (
        <TouchableOpacity onPress={clearError} style={styles.errorBox}>
          <Text style={styles.errorText}>{error} (tap to dismiss)</Text>
        </TouchableOpacity>
      )}
    </ScrollView>
  );
}

// ============================================================
// STYLES
// ============================================================

const styles = StyleSheet.create({
  scroll: { flex: 1 },
  scrollContent: { paddingBottom: 20 },
  body: { paddingHorizontal: 14 },
  loadingBox: { padding: 24, alignItems: "center" },

  // CTA
  ctaBox: {
    margin: 14,
    padding: 18,
    borderWidth: 1,
    borderRadius: 14,
    alignItems: "center",
  },
  startBtn: {
    paddingHorizontal: 22,
    paddingVertical: 13,
    borderRadius: 24,
    marginTop: 4,
  },
  startText: { color: "#fff", fontSize: 15, fontWeight: "700" },

  // Phase common
  subtle: { fontSize: 12, marginBottom: 10, marginTop: 4 },
  advanceBtn: {
    paddingHorizontal: 18,
    paddingVertical: 12,
    borderRadius: 24,
    marginTop: 12,
    alignItems: "center",
  },
  advanceText: { color: "#fff", fontSize: 14, fontWeight: "600" },
  endRow: { flexDirection: "row", gap: 8 },

  // Answer phase
  inputRow: { flexDirection: "row", alignItems: "flex-end", gap: 8 },
  input: {
    flex: 1,
    minHeight: 44,
    maxHeight: 120,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 14,
    borderWidth: 1,
    fontSize: 14,
  },
  submitBtn: {
    paddingHorizontal: 14,
    paddingVertical: 12,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
  },
  submitText: { color: "#fff", fontSize: 14, fontWeight: "600" },
  statusBox: {
    padding: 12,
    borderRadius: 12,
    borderWidth: 1,
    alignItems: "center",
  },
  statusText: { fontSize: 13 },

  // Voting / reveal
  answerCard: {
    padding: 12,
    borderRadius: 12,
    borderWidth: 1,
    marginVertical: 4,
  },
  answerContent: { fontSize: 15, lineHeight: 21, marginBottom: 6 },
  answerMetaRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  answerAuthor: { fontSize: 11, fontStyle: "italic" },
  voteCount: { fontSize: 12, fontWeight: "700" },

  // Reveal
  winnerCard: {
    padding: 16,
    borderRadius: 14,
    borderWidth: 2,
    alignItems: "center",
    marginBottom: 14,
  },
  winnerEmoji: { fontSize: 40, marginBottom: 6 },
  winnerLabel: {
    fontSize: 11,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  winnerName: { fontSize: 18, fontWeight: "700", marginTop: 4 },

  // Errors
  errorBox: {
    backgroundColor: "#FEE2E2",
    padding: 10,
    borderRadius: 10,
    margin: 14,
  },
  errorText: { color: "#991B1B", fontSize: 12 },
});
