#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${AGENT_LOG_DIR:-$SCRIPT_DIR/.logs}"
mkdir -p "$LOG_DIR"

# Use Granite 4.2 8B by default while allowing explicit environment overrides.
export DEVELOPER_MODEL="${DEVELOPER_MODEL:-ollama:granite4.2:8b}"
export STATUS_MODEL="${STATUS_MODEL:-ollama:granite4.2:8b}"
export COMPUTING_MODEL="${COMPUTING_MODEL:-ollama:granite4.2:8b}"
export LAB_MODEL="${LAB_MODEL:-ollama:granite4.2:8b}"

DEVELOPER_LOG="$LOG_DIR/developer.log"
STATUS_LOG="$LOG_DIR/status.log"
COMPUTING_LOG="$LOG_DIR/computing.log"
LAB_LOG="$LOG_DIR/lab.log"
: > "$DEVELOPER_LOG"
: > "$STATUS_LOG"
: > "$COMPUTING_LOG"
: > "$LAB_LOG"

echo "=========================================="
echo "🚀 Starting Quantum Lab Agent System"
echo "=========================================="
echo ""
echo "📋 System Architecture:"
echo "  🔹 Developer Agent (Port 8001) - Code Generation"
echo "  🔹 Status Agent (Port 8002) - Status Queries"
echo "  🔹 Computing Agent (Port 8003) - Circuit Execution"
echo "  🔹 Lab Agent (Port 8000) - Orchestrator"
echo ""
echo "=========================================="
echo ""

# Function to check if a port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo "⚠️  Warning: Port $1 is already in use"
        return 1
    fi
    return 0
}

# Check ports before starting
echo "🔍 Checking ports..."
PORTS_AVAILABLE=true
check_port 8001 || PORTS_AVAILABLE=false
check_port 8002 || PORTS_AVAILABLE=false
check_port 8003 || PORTS_AVAILABLE=false
check_port 8000 || PORTS_AVAILABLE=false
echo ""

if [ "$PORTS_AVAILABLE" != true ]; then
    echo "❌ Quantum agents are already running or one of their ports is occupied."
    echo "   Use ./restart_all.sh to replace the current stack without creating duplicate registrations."
    exit 1
fi

# Start Developer Agent (port 8001)
echo "🚀 Starting Developer Agent on port 8001..."
PYTHONUNBUFFERED=1 uv run python -m beeai_agents.quantum_developer_agent > >(tee -a "$DEVELOPER_LOG") 2>&1 &
DEVELOPER_PID=$!
echo "   ✅ Developer Agent started (PID: $DEVELOPER_PID)"
echo ""

# Wait for Developer to start
sleep 3

# Start Status Agent (port 8002)
echo "🚀 Starting Status Agent on port 8002..."
PYTHONUNBUFFERED=1 uv run python -m beeai_agents.quantum_status_agent > >(tee -a "$STATUS_LOG") 2>&1 &
STATUS_PID=$!
echo "   ✅ Status Agent started (PID: $STATUS_PID)"
echo ""

# Wait for Status to start
sleep 3

# Start Computing Agent (port 8003)
echo "🚀 Starting Computing Agent on port 8003..."
PYTHONUNBUFFERED=1 uv run python -m beeai_agents.quantum_computing_agent > >(tee -a "$COMPUTING_LOG") 2>&1 &
COMPUTING_PID=$!
echo "   ✅ Computing Agent started (PID: $COMPUTING_PID)"
echo ""

# Wait for Computing to start
sleep 3

# Start Lab Agent (port 8000)
echo "🚀 Starting Lab Agent on port 8000..."
PYTHONUNBUFFERED=1 uv run python -m beeai_agents.quantum_lab_agent > >(tee -a "$LAB_LOG") 2>&1 &
LAB_PID=$!
echo "   ✅ Lab Agent started (PID: $LAB_PID)"
echo ""

echo "=========================================="
echo "✅ All agents started successfully!"
echo "=========================================="
echo ""
echo "📊 Agent Details:"
echo "  🔹 Developer Agent:"
echo "     - PID: $DEVELOPER_PID"
echo "     - URL: http://127.0.0.1:8001"
echo "     - Model: $DEVELOPER_MODEL"
echo "     - Role: Code Generation & Explanations"
echo ""
echo "  🔹 Status Agent:"
echo "     - PID: $STATUS_PID"
echo "     - URL: http://127.0.0.1:8002"
echo "     - Model: $STATUS_MODEL"
echo "     - Role: Backend & Job Status Queries"
echo ""
echo "  🔹 Computing Agent:"
echo "     - PID: $COMPUTING_PID"
echo "     - URL: http://127.0.0.1:8003"
echo "     - Model: $COMPUTING_MODEL"
echo "     - Role: Circuit Execution"
echo ""
echo "  🔹 Lab Agent:"
echo "     - PID: $LAB_PID"
echo "     - URL: http://127.0.0.1:8000"
echo "     - Model: $LAB_MODEL"
echo "     - Role: Main Orchestrator"
echo ""
echo "=========================================="
echo ""
echo "💡 Tips:"
echo "  - Use Lab Agent (port 8000) as main entry point"
echo "  - Developer, Status, and Computing agents are invoked automatically via A2A"
echo "  - View all logs with: ./view_logs.sh"
echo "  - Press Ctrl+C to stop all agents"
echo ""
echo "🛑 To stop all agents, run:"
echo "   kill $DEVELOPER_PID $STATUS_PID $COMPUTING_PID $LAB_PID"
echo ""
echo "=========================================="

# Wait for all background processes
wait

# Made with Bob
