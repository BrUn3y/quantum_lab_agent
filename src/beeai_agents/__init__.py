"""
BeeAI Agents Package - Quantum Lab Agent System
================================================

Sistema de agentes especializados en computación cuántica con arquitectura A2A:

AGENTES:
- Quantum Developer Agent: Experto en generación de código Qiskit y OpenQASM
- Quantum Operations Agent: Orquestador de operaciones cuánticas en IBM Quantum
- [LEGACY] Quantum Lab Agent: Agente monolítico original

HERRAMIENTAS (tools/):
- IBMQuantumTool: Ejecuta circuitos cuánticos en IBM Quantum
- IBMQuantumStatusTool: Consulta computadoras cuánticas disponibles
- IBMQuantumInfoTool: Información detallada de backends
- IBMQuantumJobTool: Estado y resultados de trabajos
- QuantumDeveloperClient: Cliente A2A para invocar al Developer Agent

USAGE:
    Iniciar Developer Agent (Puerto 8001):
    ```
    python -m beeai_agents.quantum_developer_agent
    ```
    
    Iniciar Operations Agent (Puerto 8000):
    ```
    python -m beeai_agents.quantum_operations_agent
    ```
    
    O usar scripts:
    ```
    ./start_all.sh
    ```
"""

# Importar herramientas desde la carpeta tools
from .tools import (
    IBMQuantumTool,
    IBMQuantumStatusTool,
    IBMQuantumInfoTool,
    IBMQuantumJobTool,
    QuantumDeveloperClient,
)

# Importar agentes (legacy para compatibilidad)
try:
    from .agent import server, run, quantum_lab_agent, create_quantum_agent, test_quantum_agent
    _legacy_available = True
except ImportError:
    _legacy_available = False

__all__ = [
    # Herramientas
    "IBMQuantumTool",
    "IBMQuantumStatusTool",
    "IBMQuantumInfoTool",
    "IBMQuantumJobTool",
    "QuantumDeveloperClient",
]

# Agregar exports legacy si están disponibles
if _legacy_available:
    __all__.extend([
        "server",
        "run",
        "quantum_lab_agent",
        "create_quantum_agent",
        "test_quantum_agent",
    ])

__version__ = "2.0.0"  # Nueva versión con arquitectura A2A

# Made with Bob
