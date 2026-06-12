#!/bin/bash
# =============================================================
# test/e2e.sh — End-to-end integration test for PortAutopsy
# =============================================================
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

PASS=0
FAIL=0

pass() { echo "   ✓ $1"; PASS=$((PASS+1)); }
fail() { echo "   ✗ $1"; FAIL=$((FAIL+1)); }

echo ""
echo "=== PortAutopsy E2E Integration Test ==="
echo ""

# ---------------------------------------------------------
# 1. Start server in background
# ---------------------------------------------------------
echo "1. Starting server..."
uvicorn server:app --port 8001 &
SERVER_PID=$!
sleep 3

# Ensure server is killed on exit
cleanup() {
    echo ""
    echo "6. Cleanup"
    kill $SERVER_PID 2>/dev/null || true
    wait $SERVER_PID 2>/dev/null || true
    # Clean up test artifacts
    rm -f traces.jsonl traces.db saved_state.json autopsy_report.json
    echo ""
    echo "=== Results: $PASS passed, $FAIL failed ==="
    if [ $FAIL -gt 0 ]; then
        exit 1
    fi
}
trap cleanup EXIT

# ---------------------------------------------------------
# 2. Health check
# ---------------------------------------------------------
echo "2. Checking API health..."
if curl -sf http://localhost:8001/health > /dev/null 2>&1; then
    pass "/health returns 200"
else
    fail "/health unreachable"
fi

# ---------------------------------------------------------
# 3. Run simulation
# ---------------------------------------------------------
echo "3. Running simulation..."
python demo/run_port.py --fresh

if [ -f traces.jsonl ]; then
    pass "traces.jsonl exists"
else
    fail "traces.jsonl missing"
fi

if [ -f traces.db ]; then
    pass "traces.db exists"
else
    fail "traces.db missing"
fi

if [ -f saved_state.json ]; then
    pass "saved_state.json exists"
else
    fail "saved_state.json missing"
fi

# ---------------------------------------------------------
# 4. Inject cold-chain failure
# ---------------------------------------------------------
echo "4. Injecting cold-chain failure..."
python demo/inject_failure.py cold_chain
pass "Failure injected"

# ---------------------------------------------------------
# 5. Check API endpoints
# ---------------------------------------------------------
echo "5. Checking API endpoints..."

if curl -sf http://localhost:8001/traces > /dev/null 2>&1; then
    pass "/traces"
else
    fail "/traces"
fi

if curl -sf http://localhost:8001/causal-graph > /dev/null 2>&1; then
    pass "/causal-graph"
else
    fail "/causal-graph"
fi

if curl -sf http://localhost:8001/metrics > /dev/null 2>&1; then
    pass "/metrics"
else
    fail "/metrics"
fi

echo ""
echo "=== E2E test complete ==="
