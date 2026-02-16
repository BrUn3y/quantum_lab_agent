"""
BeeAI Agents Package - Quantum Lab Agent System
================================================

Sistema de agentes especializados en computación cuántica con arquitectura A2A:

AGENTES:
- Quantum Operations Agent: Orquestador principal (Puerto 8000)
- Quantum Developer Agent: Generación de código Qiskit/OpenQASM (Puerto 8001)
- Quantum Status Agent: Consultas de backends y jobs (Puerto 8002)
- Quantum Computing Agent: Ejecución de circuitos cuánticos (Puerto 8003)

HERRAMIENTAS (tools/):
- IBMQuantumTool: Ejecuta circuitos cuánticos en IBM Quantum
- IBMQuantumStatusTool: Consulta computadoras cuánticas disponibles
- IBMQuantumInfoTool: Información detallada de backends
- IBMQuantumJobTool: Estado y resultados de trabajos
- QuantumDeveloperClient: Cliente A2A para invocar al Developer Agent
- QuantumStatusClient: Cliente A2A para invocar al Status Agent
- QuantumComputingClient: Cliente A2A para invocar al Computing Agent

USAGE:
    Iniciar todos los agentes:
    ```
    ./start_all.sh
    ```
    
    O iniciar individualmente:
    ```
    ./start_developer.sh   # Puerto 8001
    ./start_status.sh      # Puerto 8002
    ./start_computing.sh   # Puerto 8003
    ./start_operations.sh  # Puerto 8000 (iniciar al final)
    ```
"""

# Importar herramientas desde la carpeta tools
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
    # Herramientas IBM Quantum
    "IBMQuantumTool",
    "IBMQuantumStatusTool",
    "IBMQuantumInfoTool",
    "IBMQuantumJobTool",
    # Clientes A2A
    "QuantumDeveloperClient",
    "QuantumStatusClient",
    "QuantumComputingClient",
]

__version__ = "2.0.0"  # Arquitectura A2A con 4 agentes especializados
