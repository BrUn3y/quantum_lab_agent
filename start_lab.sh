#!/bin/bash

# Script to start the Quantum Lab Agent
# Port: 8000
# Model: Mistral Small

echo "=================================="
echo "⚡ Quantum Lab Agent"
echo "=================================="
echo ""
echo "Starting main orchestrator agent..."
echo "Port: 8000"
echo "Model: Mistral Small"
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

# Start the Lab Agent
uv run python3 -m beeai_agents.quantum_lab_agent

# Made with Bob
