#!/bin/bash
export COMPUTING_MODEL="${COMPUTING_MODEL:-ollama:granite4.2:8b}"
echo "🚀 Starting Quantum Computing Agent..."
echo "🔬 Port: 8003"
echo "🤖 Model: $COMPUTING_MODEL"
echo ""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${AGENT_LOG_DIR:-$SCRIPT_DIR/.logs}"
mkdir -p "$LOG_DIR"
: > "$LOG_DIR/computing.log"
set -o pipefail
PYTHONUNBUFFERED=1 uv run python -m beeai_agents.quantum_computing_agent 2>&1 | tee -a "$LOG_DIR/computing.log"

# Made with Bob
