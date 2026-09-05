#!/bin/bash
export EXPERIMENT_MODEL="${EXPERIMENT_MODEL:-ollama:granite4.2:8b}"
echo "🧪 Starting Quantum Experiment Agent (Development)..."
echo "🔬 Port: 8004"
echo "🤖 Model: $EXPERIMENT_MODEL"
echo ""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${AGENT_LOG_DIR:-$SCRIPT_DIR/.logs}"
mkdir -p "$LOG_DIR"
: > "$LOG_DIR/experiment.log"
set -o pipefail
PYTHONUNBUFFERED=1 uv run python -m beeai_agents.quantum_experiment_agent 2>&1 | tee -a "$LOG_DIR/experiment.log"
