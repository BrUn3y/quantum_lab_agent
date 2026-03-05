"""
BeeAI Agents Package - Quantum Lab Agent System
================================================

Specialized quantum computing agent system with A2A architecture:

AGENTS:
- Quantum Lab Agent: Main orchestrator (Port 8000)
- Quantum Developer Agent: Qiskit/OpenQASM code generation (Port 8001)
- Quantum Status Agent: Backend and job queries (Port 8002)
- Quantum Computing Agent: Quantum circuit execution (Port 8003)

TOOLS (tools/):
- IBMQuantumTool: Executes quantum circuits on IBM Quantum
- IBMQuantumStatusTool: Queries available quantum computers
- IBMQuantumInfoTool: Detailed backend information
- IBMQuantumJobTool: Job status and results
- QuantumDeveloperClient: A2A client to invoke the Developer Agent
- QuantumStatusClient: A2A client to invoke the Status Agent
- QuantumComputingClient: A2A client to invoke the Computing Agent

USAGE:
    Start all agents:
    ```
    ./start_all.sh
    ```
    
    Or start individually:
    ```
    ./start_developer.sh   # Port 8001
    ./start_status.sh      # Port 8002
    ./start_computing.sh   # Port 8003
    ./start_operations.sh  # Port 8000 (start at the end)
    ```
"""

# Import tools from the tools folder
from .tools import (
    IBMQuantumTool,
    IBMQuantumStatusTool,
    IBMQuantumInfoTool,
    IBMQuantumJobTool,
    QuantumDeveloperClient,
    QuantumStatusClient,
    QuantumComputingClient,
)

__all__ = [
    # IBM Quantum Tools
    "IBMQuantumTool",
    "IBMQuantumStatusTool",
    "IBMQuantumInfoTool",
    "IBMQuantumJobTool",
    # A2A Clients
    "QuantumDeveloperClient",
    "QuantumStatusClient",
    "QuantumComputingClient",
]

__version__ = "2.0.0"  # A2A architecture with 4 specialized agents
