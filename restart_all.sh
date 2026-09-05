#!/bin/bash

# Restarts the full Quantum Lab Agent system: stops anything already
# listening on the agents' ports (and any stray agent process), then
# starts everything again via start_all.sh.

DEVELOPER_PORT="${DEVELOPER_PORT:-8001}"
STATUS_PORT="${STATUS_PORT:-8002}"
COMPUTING_PORT="${COMPUTING_PORT:-8003}"
LAB_PORT="${LAB_PORT:-8000}"

echo "=========================================="
echo "🔄 Restarting Quantum Lab Agent System"
echo "=========================================="
echo ""

# Stops whatever is listening on a given port, escalating to SIGKILL
# if it doesn't exit gracefully within a few seconds.
kill_port() {
    local port="$1"
    local name="$2"
    local pids
    pids=$(lsof -ti tcp:"$port" 2>/dev/null)

    if [ -z "$pids" ]; then
        echo "   ⚪ $name (port $port): not running"
        return
    fi

    echo "   🛑 $name (port $port): stopping PID(s) $pids"
    kill $pids 2>/dev/null

    for _ in 1 2 3 4 5; do
        sleep 1
        pids=$(lsof -ti tcp:"$port" 2>/dev/null)
        [ -z "$pids" ] && break
    done

    if [ -n "$pids" ]; then
        echo "      ⚠️  Still running, forcing kill -9 on PID(s) $pids"
        kill -9 $pids 2>/dev/null
    fi
}

echo "🔍 Stopping existing agents..."
kill_port "$DEVELOPER_PORT" "Developer Agent"
kill_port "$STATUS_PORT" "Status Agent"
kill_port "$COMPUTING_PORT" "Computing Agent"
kill_port "$LAB_PORT" "Lab Agent"

# Fallback: catch any agent process that isn't bound to its port yet
# (e.g. it crashed mid-startup, before opening the listening socket).
for module in quantum_developer_agent quantum_status_agent quantum_computing_agent quantum_lab_agent; do
    pkill -f "beeai_agents.$module" 2>/dev/null
done

echo ""
echo "✅ All agents stopped"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/start_all.sh"
