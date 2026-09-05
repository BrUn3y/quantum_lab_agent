#!/bin/bash

export LAB_MODEL="${LAB_MODEL:-ollama:granite4.2:8b}"

# Script to start the Quantum Lab Agent
# Port: 8000
# Model: Granite 4.2 8B via Ollama

echo "=================================="
echo "⚡ Quantum Lab Agent"
echo "=================================="
echo ""
echo "Starting main orchestrator agent..."
echo "Port: 8000"
echo "Model: $LAB_MODEL"
echo ""
echo "⚠️  IMPORTANT: Make sure the Developer Agent is running on port 8001"
echo ""
echo "Press Ctrl+C to stop"
echo "=================================="
echo ""

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Start the Lab Agent and retain its output for view_logs.sh.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${AGENT_LOG_DIR:-$SCRIPT_DIR/.logs}"
mkdir -p "$LOG_DIR"
: > "$LOG_DIR/lab.log"
set -o pipefail
PYTHONUNBUFFERED=1 uv run python3 -m beeai_agents.quantum_lab_agent 2>&1 | tee -a "$LOG_DIR/lab.log"

# Made with Bob
