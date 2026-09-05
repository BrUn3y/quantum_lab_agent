#!/bin/bash
export STATUS_MODEL="${STATUS_MODEL:-ollama:granite4.2:8b}"
echo "🚀 Starting Quantum Status Agent..."
echo "📊 Port: 8002"
echo "🤖 Model: $STATUS_MODEL"
echo ""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${AGENT_LOG_DIR:-$SCRIPT_DIR/.logs}"
mkdir -p "$LOG_DIR"
: > "$LOG_DIR/status.log"
set -o pipefail
PYTHONUNBUFFERED=1 uv run python -m beeai_agents.quantum_status_agent 2>&1 | tee -a "$LOG_DIR/status.log"

# Made with Bob
