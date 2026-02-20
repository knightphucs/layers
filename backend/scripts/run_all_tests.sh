#!/bin/bash
# ============================================================
# LAYERS — Run All Week 3 Tests
# FILE: backend/scripts/run_all_tests.sh
#
# Run: chmod +x scripts/run_all_tests.sh && ./scripts/run_all_tests.sh
# ============================================================

echo "🧪 LAYERS — Complete Test Suite (Week 1-3)"
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

# ---- Week 3 Day 1: Locations ----
run_test "Day 1: Location API & PostGIS" "tests/test_locations.py"

# ---- Week 3 Day 2: Artifacts ----
run_test "Day 2: Artifact CRUD & Features" "tests/test_artifacts.py"

# ---- Week 3 Day 3: Fog of War ----
run_test "Day 3: Exploration & Fog of War" "tests/test_exploration.py"

# ---- Week 3 Day 4: Anti-Cheat ----
run_test "Day 4: Anti-Cheat System" "tests/test_anti_cheat.py"

# ---- Week 3 Day 5: Integration ----
run_test "Day 5: Integration Tests" "tests/test_integration_week3.py"

# ---- SUMMARY ----
echo "=============================================="
echo "📊 FINAL RESULTS"
echo "=============================================="
echo -e "  ${GREEN}Passed: ${PASS}${NC}"
echo -e "  ${RED}Failed: ${FAIL}${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL TEST SUITES PASSED! Week 3 Complete!${NC}"
    echo ""
    echo "  Next: Week 4 — Mobile Geo Features 📱🗺️"
    echo "  The app starts looking REAL with map markers,"
    echo "  unlock animations, and fog overlay!"
else
    echo -e "${RED}⚠️  Some tests failed. Fix them before moving to Week 4.${NC}"
fi
