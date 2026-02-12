#!/bin/bash

# Script para iniciar ambos agentes en terminales separadas
# Requiere: tmux o screen (opcional)

echo "=================================="
echo "🚀 Quantum Lab Agent System"
echo "=================================="
echo ""
echo "Iniciando sistema completo de agentes A2A..."
echo ""

# Verificar si tmux está instalado
if command -v tmux &> /dev/null; then
    echo "✅ Usando tmux para gestionar las sesiones"
    echo ""
    
    # Crear sesión de tmux
    tmux new-session -d -s quantum_agents
    
    # Ventana 1: Developer Agent
    tmux rename-window -t quantum_agents:0 'Developer'
    tmux send-keys -t quantum_agents:0 'bash start_developer.sh' C-m
    
    # Ventana 2: Operations Agent
    tmux new-window -t quantum_agents:1 -n 'Operations'
    tmux send-keys -t quantum_agents:1 'sleep 5 && bash start_operations.sh' C-m
    
    # Adjuntar a la sesión
    echo "=================================="
    echo "✅ Agentes iniciados en tmux"
    echo ""
    echo "Para ver los agentes:"
    echo "  tmux attach -t quantum_agents"
    echo ""
    echo "Para navegar entre ventanas:"
    echo "  Ctrl+B, luego 0 (Developer) o 1 (Operations)"
    echo ""
    echo "Para detener todo:"
    echo "  tmux kill-session -t quantum_agents"
    echo "=================================="
    
    tmux attach -t quantum_agents
    
else
    echo "⚠️  tmux no está instalado"
    echo ""
    echo "Por favor, inicia los agentes manualmente en terminales separadas:"
    echo ""
    echo "Terminal 1:"
    echo "  bash start_developer.sh"
    echo ""
    echo "Terminal 2:"
    echo "  bash start_operations.sh"
    echo ""
    echo "O instala tmux:"
    echo "  macOS: brew install tmux"
    echo "  Linux: sudo apt-get install tmux"
    echo "=================================="
fi

# Made with Bob
