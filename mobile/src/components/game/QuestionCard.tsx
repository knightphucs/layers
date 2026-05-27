/**
 * LAYERS — QuestionCard Component
 * ================================================
 * The big card at the top of the GamePanel showing the current question.
 */

import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { Colors } from "../../constants/colors";
import { useAuthStore } from "../../store/authStore";
import { GameRound, RoundState } from "../../types/game";

interface QuestionCardProps {
  round: GameRound;
}

const STATE_LABEL: Record<RoundState, string> = {
  ANSWERING: "✍️ Answering",
  VOTING: "🗳️ Voting",
  REVEALED: "🎉 Revealed",
};

const STATE_COLOR: Record<RoundState, string> = {
  ANSWERING: "#3B82F6",
  VOTING: "#F59E0B",
  REVEALED: "#10B981",
};

function QuestionCardComponent({ round }: QuestionCardProps) {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  return (
    <View
      style={[
        styles.card,
        { backgroundColor: colors.surface, borderColor: colors.border },
      ]}
    >
      <View style={styles.headerRow}>
        <Text style={[styles.roundLabel, { color: colors.textSecondary }]}>
          Round {round.round_number}
        </Text>
        <View
          style={[
            styles.stateBadge,
            { backgroundColor: STATE_COLOR[round.state] + "20" },
          ]}
        >
          <Text style={[styles.stateText, { color: STATE_COLOR[round.state] }]}>
            {STATE_LABEL[round.state]}
          </Text>
        </View>
      </View>

      <Text style={[styles.question, { color: colors.text }]}>
        {round.question_text}
      </Text>
    </View>
  );
}

export const QuestionCard = React.memo(QuestionCardComponent);
QuestionCard.displayName = "QuestionCard";

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderRadius: 16,
    padding: 16,
    marginHorizontal: 12,
    marginVertical: 10,
  },
  headerRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 10,
  },
  roundLabel: {
    fontSize: 12,
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  stateBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  stateText: {
    fontSize: 11,
    fontWeight: "600",
  },
  question: {
    fontSize: 19,
    lineHeight: 26,
    fontWeight: "500",
  },
});

export default QuestionCard;
