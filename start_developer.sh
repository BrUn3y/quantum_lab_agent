#!/bin/bash

# Script para iniciar el Quantum Developer Agent
# Puerto: 8001
# Modelo: Granite 4 Small Hybrid mediante Ollama

echo "=================================="
echo "🎯 Quantum Developer Agent"
echo "=================================="
echo ""
echo "Iniciando agente experto en código cuántico..."
echo "Puerto: 8001"
echo "Modelo: granite4:small-h (Ollama)"
echo ""
echo "Presiona Ctrl+C para detener"
echo "=================================="
echo ""

# Activar entorno virtual si existe
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Iniciar el Developer Agent
uv run python3 -m beeai_agents.quantum_developer_agent

# Made with Bob
