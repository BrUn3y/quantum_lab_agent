#!/bin/bash
echo "🚀 Starting Quantum Status Agent..."
echo "📊 Port: 8002"
echo "🤖 Model: granite4.2:8b (Ollama)"
echo ""
uv run python -m beeai_agents.quantum_status_agent

# Made with Bob
