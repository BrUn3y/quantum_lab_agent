"""
Quantum Computing Agent - Especialista en Ejecución de Circuitos Cuánticos

Este agente es un especialista en:
- Ejecutar código QASM/Qiskit en computadoras cuánticas de IBM
- Gestionar la ejecución en simuladores y hardware real
- Proporcionar información detallada de trabajos ejecutados
- Transpilación automática de circuitos

Modelo: mistralai/mistral-small-3-1-24b-instruct-2503 (Watsonx)
Puerto: 8003
Tipo: Servidor A2A usando BeeAI Framework (ReActAgent con IBMQuantumTool)
"""

import os

from beeai_framework.adapters.a2a import A2AServer, A2AServerConfig
from beeai_framework.agents.react import ReActAgent
from beeai_framework.backend import ChatModel
from beeai_framework.memory import UnconstrainedMemory
from beeai_framework.serve.utils import LRUMemoryManager

# Importar la herramienta de ejecución
from .tools import IBMQuantumTool

# Instrucciones para el Computing Agent (sin template personalizado para evitar errores de parsing)
COMPUTING_INSTRUCTIONS = """Eres el Quantum Computing Agent. Ejecutas circuitos cuánticos en IBM Quantum.

⚠️ REGLA CRÍTICA: Tu respuesta SIEMPRE debe incluir el Job ID de forma prominente.

PASOS:
1. Extraer código QASM del request del usuario
2. Identificar backend (si se especifica, sino usar ibm_kyiv)
3. Ejecutar con ibm_quantum_executor
4. En tu respuesta final, SIEMPRE incluir:
   - ⚠️ **Job ID: [el_job_id_real]** (en negrita y con emoji de advertencia)
   - Backend usado
   - Shots
   - Resultados (si están disponibles)

FORMATO DE RESPUESTA:
```
🚀 Circuito ejecutado exitosamente

⚠️ **Job ID: abc123xyz456** ← ESTO ES OBLIGATORIO

Backend: ibm_torino
Shots: 1024
Estado: DONE

[Resultados si están disponibles]
```

El Job ID es CRÍTICO porque las computadoras cuánticas tardan en responder y el usuario necesita el ID para consultar resultados después.
"""

def create_computing_agent():
    """Crea una instancia del Quantum Computing Agent con Mistral Small usando ReActAgent"""
    # Configurar Watsonx con Mistral Small
    llm = ChatModel.from_name(
        f"watsonx:{os.getenv('WATSONX_COMPUTING_MODEL', 'mistralai/mistral-small-3-1-24b-instruct-2503')}"
    )
    
    # Crear el agente usando ReActAgent (sin template personalizado para evitar errores de parsing)
    # Las instrucciones se pasarán en el prompt al ejecutar
    return ReActAgent(
        llm=llm,
        tools=[IBMQuantumTool()],
        memory=UnconstrainedMemory(),
    )

def run():
    """Inicia el servidor A2A del Quantum Computing Agent usando BeeAI Framework"""
    port = int(os.getenv("COMPUTING_PORT", 8003))
    host = os.getenv("COMPUTING_HOST", "127.0.0.1")
    
    print("=" * 60)
    print("🚀 Starting Quantum Computing Agent Server (BeeAI A2A)")
    print("=" * 60)
    print(f"  🔬 Agent: Quantum Computing Agent (ReActAgent)")
    print(f"  🤖 Model: {os.getenv('WATSONX_COMPUTING_MODEL', 'mistralai/mistral-small-3-1-24b-instruct-2503')}")
    print(f"  🌐 Host: {host}")
    print(f"  🔌 Port: {port}")
    print(f"  🛠️  Tools: 1 (IBM Quantum Executor)")
    print(f"  📚 Skills: Circuit Execution")
    print(f"  🔧 Framework: BeeAI A2A Server (ReActAgent)")
    print("=" * 60)
    
    # Crear el agente
    agent = create_computing_agent()
    
    # Configurar y ejecutar el servidor A2A
    # Usamos LRU memory manager para mantener un número limitado de sesiones en memoria
    A2AServer(
        config=A2AServerConfig(
            port=port,
            host=host,
            protocol="jsonrpc"  # Protocolo JSON-RPC para A2A
        ),
        memory_manager=LRUMemoryManager(maxsize=100)
    ).register(agent, send_trajectory=True).serve()

if __name__ == "__main__":
    run()

# Made with Bob