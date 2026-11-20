#!/bin/bash
# ============================================================
# LAYERS — Run the full test suite, grouped by feature area
# FILE: backend/scripts/run_all_tests.sh
#
# Run: chmod +x scripts/run_all_tests.sh && ./scripts/run_all_tests.sh
#
# Requires a live Postgres + PostGIS at TEST_DATABASE_URL.
# ============================================================

echo "🧪 LAYERS — Complete Test Suite"
echo "=============================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0

run_test() {
    local name=$1
    local file=$2
    echo -e "${YELLOW}▶ Running: ${name}${NC}"
    
    if pytest "$file" -v --tb=short 2>&1 | tail -20; then
        echo -e "${GREEN}✅ ${name} PASSED${NC}"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}❌ ${name} FAILED${NC}"
        FAIL=$((FAIL + 1))
    fi
    echo ""
}

# ---- Week 1: Auth ----
run_test "Week 1: Authentication" "tests/test_auth.py"

# ---- Week 3: Geo ----
run_test "Location API & PostGIS" "tests/test_locations.py"
run_test "Artifact CRUD & Features" "tests/test_artifacts.py"
run_test "Exploration & Fog of War" "tests/test_exploration.py"
run_test "Anti-Cheat System" "tests/test_anti_cheat.py"
run_test "Integration" "tests/test_integration.py"

# ---- Week 5: Social foundation ----
run_test "Notifications" "tests/test_notifications.py"
run_test "Connections" "tests/test_connections.py"

# ---- Week 6: Chat, campfires, spark, games ----
run_test "Chat REST" "tests/test_chat_rest.py"
run_test "Chat WebSocket" "tests/test_chat_websocket.py"
run_test "WS Pub/Sub (multi-worker)" "tests/test_ws_pubsub.py"
run_test "Campfires" "tests/test_campfire.py"
run_test "Social Spark" "tests/test_social_spark.py"
run_test "Truth or Dare" "tests/test_truth_or_dare.py"

# ---- Week 7: Gamification ----
run_test "XP Service" "tests/test_xp_service.py"
run_test "Quest Service" "tests/test_quest_service.py"
run_test "Badges & Leaderboard" "tests/test_gamification.py"

# ---- Week 8: Trust & safety, hardening ----
run_test "Moderation" "tests/test_moderation.py"
run_test "Reputation & Reports" "tests/test_reputation.py"
run_test "Admin Panel" "tests/test_admin.py"
run_test "Shadow Layer" "tests/test_shadow.py"
run_test "Security Hardening" "tests/test_security_hardening.py"
run_test "Week 8 Integration" "tests/test_week8_integration.py"

# ---- Infrastructure ----
run_test "Redis Cache" "tests/test_cache.py"
run_test "Redis Rate Limiting" "tests/test_rate_limit_redis.py"
run_test "Presence & Geo Cache" "tests/test_presence_geocache.py"

# ---- SUMMARY ----
echo "=============================================="
echo "📊 FINAL RESULTS"
echo "=============================================="
echo -e "  ${GREEN}Passed: ${PASS}${NC}"
echo -e "  ${RED}Failed: ${FAIL}${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL TEST SUITES PASSED${NC}"
else
    echo -e "${RED}⚠️  Some suites failed — see the output above.${NC}"
fi

echo ""
echo "Note: plain 'pytest' runs the same files in one process and is faster."
echo "This script exists to show pass/fail per feature area."
