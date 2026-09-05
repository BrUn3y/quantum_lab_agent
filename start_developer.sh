#!/bin/bash

export DEVELOPER_MODEL="${DEVELOPER_MODEL:-ollama:granite4.2:8b}"

# Script para iniciar el Quantum Developer Agent
# Puerto: 8001
# Modelo: Granite 4.2 8B mediante Ollama

echo "=================================="
echo "🎯 Quantum Developer Agent"
echo "=================================="
echo ""
echo "Iniciando agente experto en código cuántico..."
echo "Puerto: 8001"
echo "Modelo: $DEVELOPER_MODEL"
echo ""
echo "Presiona Ctrl+C para detener"
echo "=================================="
echo ""

# Activar entorno virtual si existe
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Iniciar el Developer Agent y conservar su salida para view_logs.sh.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${AGENT_LOG_DIR:-$SCRIPT_DIR/.logs}"
mkdir -p "$LOG_DIR"
: > "$LOG_DIR/developer.log"
set -o pipefail
PYTHONUNBUFFERED=1 uv run python3 -m beeai_agents.quantum_developer_agent 2>&1 | tee -a "$LOG_DIR/developer.log"

# Made with Bob
