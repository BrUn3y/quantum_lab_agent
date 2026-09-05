#!/bin/bash
echo "🚀 Starting Quantum Status Agent..."
echo "📊 Port: 8002"
echo "🤖 Model: granite4:small-h (Ollama)"
echo ""
uv run python -m beeai_agents.quantum_status_agent

# Made with Bob
