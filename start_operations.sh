#!/bin/bash

# Script para iniciar el Quantum Operations Agent
# Puerto: 8000
# Modelo: Mistral Small

echo "=================================="
echo "⚡ Quantum Operations Agent"
echo "=================================="
echo ""
echo "Iniciando agente orquestador principal..."
echo "Puerto: 8000"
echo "Modelo: Mistral Small"
echo ""
echo "⚠️  IMPORTANTE: Asegúrate de que el Developer Agent esté corriendo en el puerto 8001"
echo ""
echo "Presiona Ctrl+C para detener"
echo "=================================="
echo ""

# Activar entorno virtual si existe
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Iniciar el Operations Agent
python3 -m beeai_agents.quantum_operations_agent

# Made with Bob
